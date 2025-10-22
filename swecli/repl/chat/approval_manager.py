"""Approval manager for chat interface with interactive prompts."""


class ChatApprovalManager:
    """Approval manager for chat interface with interactive prompts."""

    def __init__(self, console, chat_app=None):
        self.console = console
        self.chat_app = chat_app  # Reference to chat application for run_in_terminal
        self.auto_approve_remaining = False
        self.approved_patterns = set()
        self.pre_approved_commands = set()  # Commands that were already approved

        # Initialize rules manager for Phase 3
        from swecli.core.approval import ApprovalRulesManager, RuleAction

        self.rules_manager = ApprovalRulesManager()
        self.RuleAction = RuleAction  # Store for use in methods

    def _check_auto_approval(self, operation, command):
        """Check if operation should be auto-approved.

        Args:
            operation: Operation to check
            command: Command string

        Returns:
            ApprovalResult if auto-approved, None otherwise
        """
        from swecli.core.approval import ApprovalResult, ApprovalChoice
        from swecli.models.operation import OperationType

        # Only show approval for bash commands
        if operation and operation.type != OperationType.BASH_EXECUTE:
            return ApprovalResult(
                approved=True,
                choice=ApprovalChoice.APPROVE,
                apply_to_all=False,
            )

        # Check if pre-approved
        if command and command in self.pre_approved_commands:
            self.pre_approved_commands.discard(command)
            return ApprovalResult(
                approved=True,
                choice=ApprovalChoice.APPROVE,
                apply_to_all=False,
            )

        # Check pattern-based auto-approval
        if command and any(pattern in command for pattern in self.approved_patterns):
            return ApprovalResult(
                approved=True,
                choice=ApprovalChoice.APPROVE_ALL,
                apply_to_all=True,
            )

        return None

    def _check_approval_rules(self, command):
        """Check and apply approval rules.

        Args:
            command: Command to check

        Returns:
            Tuple of (ApprovalResult or None, matched_rule or None)
        """
        from swecli.core.approval import ApprovalResult, ApprovalChoice

        if not command:
            return None, None

        matched_rule = self.rules_manager.evaluate_command(command)
        if not matched_rule:
            return None, None

        # Auto-approve rule
        if matched_rule.action == self.RuleAction.AUTO_APPROVE:
            self.rules_manager.add_history(command, True, rule_matched=matched_rule.id)
            # Don't show auto-approval messages in chat to reduce noise
            # self.console.print(f"[dim]✓ Auto-approved by rule: {matched_rule.name}[/dim]")
            return ApprovalResult(
                approved=True,
                choice=ApprovalChoice.APPROVE,
                apply_to_all=False,
            ), matched_rule

        # Auto-deny rule
        if matched_rule.action == self.RuleAction.AUTO_DENY:
            self.rules_manager.add_history(command, False, rule_matched=matched_rule.id)
            self.console.print(f"[red]✗ Denied by rule: {matched_rule.name}[/red]")
            return ApprovalResult(
                approved=False,
                choice=ApprovalChoice.DENY,
                cancelled=True,
            ), matched_rule

        # REQUIRE_APPROVAL or REQUIRE_EDIT - continue to modal
        return None, matched_rule

    async def _show_approval_modal(self, command, working_dir):
        """Show approval modal to user.

        Args:
            command: Command to approve
            working_dir: Working directory

        Returns:
            Tuple of (approved, choice, edited_command)
        """
        from swecli.core.approval import ApprovalResult, ApprovalChoice

        try:
            return await self.chat_app.show_approval_modal(command or "", working_dir or "")
        except Exception as e:
            # Fallback to simple prompt
            return self._fallback_prompt(command, working_dir, e)

    def _fallback_prompt(self, command, working_dir, error):
        """Fallback to simple text prompt when modal fails.

        Args:
            command: Command to approve
            working_dir: Working directory
            error: Exception that caused fallback

        Returns:
            Tuple of (approved, choice, edited_command)
        """
        import traceback

        print(f"\n\033[31mModal error: {error}\033[0m")
        print(f"\033[31mTraceback:\033[0m")
        traceback.print_exc()
        print("Falling back to simple prompt...\n")
        print("\n\033[1;33m╭─ Bash Command Approval ─╮\033[0m")
        print(f"\033[1;33m│\033[0m Command: \033[36m{command}\033[0m")
        print(f"\033[1;33m│\033[0m Working directory: {working_dir}")
        print("\033[1;33m╰──────────────────────────╯\033[0m\n")
        print("  \033[1;36m1.\033[0m Yes, run this command")
        print("  \033[1;36m2.\033[0m Yes, and don't ask again for similar commands")
        print("  \033[1;36m3.\033[0m No, cancel this operation\n")

        try:
            print("\033[1;33mChoose an option (1-3):\033[0m ", end="", flush=True)
            choice = input().strip()
            approved = choice in ["1", "2"]
            return approved, choice, command
        except (KeyboardInterrupt, EOFError):
            print("\n\033[33mOperation cancelled\033[0m")
            return False, "3", command

    def _show_edited_command(self, command, edited_command):
        """Show notification if command was edited.

        Args:
            command: Original command
            edited_command: Edited command
        """
        if edited_command != command:
            if self.chat_app:
                self.chat_app.add_assistant_message(f"Command edited to: {edited_command}")
            else:
                self.console.print(f"[yellow]Command edited to:[/yellow] {edited_command}")

    def _process_approve_choice(self, command, edited_command, matched_rule):
        """Process single approval choice.

        Args:
            command: Original command
            edited_command: Edited command
            matched_rule: Matched approval rule

        Returns:
            ApprovalResult
        """
        from swecli.core.approval import ApprovalResult, ApprovalChoice

        self._show_edited_command(command, edited_command)

        self.rules_manager.add_history(
            command,
            True,
            edited_command=edited_command if edited_command != command else None,
            rule_matched=matched_rule.id if matched_rule else None,
        )

        return ApprovalResult(
            approved=True,
            choice=ApprovalChoice.APPROVE,
            edited_content=edited_command if edited_command != command else None,
            apply_to_all=False,
        )

    def _process_approve_all_choice(self, command, edited_command, matched_rule):
        """Process approve-all choice.

        Args:
            command: Original command
            edited_command: Edited command
            matched_rule: Matched approval rule

        Returns:
            ApprovalResult
        """
        from swecli.core.approval import ApprovalResult, ApprovalChoice
        from swecli.core.approval.rules import ApprovalRule, RuleType, RuleAction
        from datetime import datetime
        import uuid

        # Store pattern for future auto-approval (in-memory for this session)
        pattern_cmd = edited_command if edited_command else command
        if pattern_cmd:
            base_cmd = " ".join(pattern_cmd.split()[:2])
            self.approved_patterns.add(base_cmd)

            # Create persistent approval rule
            rule_id = f"user_approved_{uuid.uuid4().hex[:8]}"
            rule = ApprovalRule(
                id=rule_id,
                name=f"Auto-approve: {base_cmd}",
                description=f"User approved command starting with '{base_cmd}' on {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                rule_type=RuleType.PREFIX,
                pattern=base_cmd,
                action=RuleAction.AUTO_APPROVE,
                enabled=True,
                priority=50,
                created_at=datetime.now().isoformat(),
            )
            self.rules_manager.add_rule(rule)

            if self.chat_app:
                self.chat_app.add_assistant_message(
                    f"✓ Rule created: Commands starting with '{base_cmd}' will be auto-approved"
                )

        self._show_edited_command(command, edited_command)

        self.rules_manager.add_history(
            command,
            True,
            edited_command=edited_command if edited_command != command else None,
            rule_matched=matched_rule.id if matched_rule else None,
        )

        return ApprovalResult(
            approved=True,
            choice=ApprovalChoice.APPROVE_ALL,
            edited_content=edited_command if edited_command != command else None,
            apply_to_all=True,
        )

    def _process_deny_choice(self, command, matched_rule):
        """Process denial choice.

        Args:
            command: Command that was denied
            matched_rule: Matched approval rule

        Returns:
            ApprovalResult
        """
        from swecli.core.approval import ApprovalResult, ApprovalChoice

        self.rules_manager.add_history(
            command,
            False,
            rule_matched=matched_rule.id if matched_rule else None,
        )

        return ApprovalResult(
            approved=False,
            choice=ApprovalChoice.DENY,
            edited_content=None,
            cancelled=True,
        )

    async def request_approval(
        self,
        operation: any,
        preview: str,
        allow_edit: bool = True,
        timeout: any = None,
        command: any = None,
        working_dir: any = None,
        force_prompt: bool = False,
    ):
        """Request approval for an operation with interactive prompt.

        Args:
            operation: Operation to approve
            preview: Preview text
            allow_edit: Whether editing is allowed
            timeout: Timeout for approval
            command: Command string
            working_dir: Working directory
            force_prompt: Force showing prompt

        Returns:
            ApprovalResult
        """
        # Check auto-approval conditions
        auto_result = self._check_auto_approval(operation, command)
        if auto_result:
            return auto_result

        # Check approval rules
        rule_result, matched_rule = self._check_approval_rules(command)
        if rule_result:
            return rule_result

        # Show approval modal
        approved, choice, edited_command = await self._show_approval_modal(command, working_dir)

        # Process user choice
        if choice == "1":
            return self._process_approve_choice(command, edited_command, matched_rule)
        elif choice == "2":
            return self._process_approve_all_choice(command, edited_command, matched_rule)
        else:
            return self._process_deny_choice(command, matched_rule)

    def skip_approval(self) -> bool:
        """Check if approval prompts should be skipped."""
        return self.auto_approve_remaining

    def reset_auto_approve(self) -> None:
        """Reset auto-approve setting."""
        self.auto_approve_remaining = False
