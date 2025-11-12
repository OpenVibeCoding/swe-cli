# ACE Playbook Selection Implementation Plan

## Executive Summary

**Goal**: Implement hybrid retrieval-based playbook selection to replace the current "dump all bullets" approach with intelligent, query-specific bullet selection.

**Current State**: `playbook.as_prompt()` returns ALL bullets regardless of relevance
**Target State**: `playbook.as_context(query, max_strategies=30)` returns top-K most relevant bullets

**Expected Benefits**:
- 📉 Reduced context window usage (50-80% reduction for large playbooks)
- 🎯 More relevant strategy selection
- 💰 Lower token costs
- ⚡ Faster response times
- 📈 Better scalability as playbooks grow

---

## Architecture Analysis

### Current System Components

```
┌─────────────────────────────────────────────────────────────┐
│ query_processor.py (_prepare_messages)                      │
│  ├─ playbook = session.get_playbook()                       │
│  └─ playbook_context = playbook.as_prompt()  ❌ ALL BULLETS │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Playbook (swecli/core/context_management/playbook.py)       │
│  ├─ Bullet: {id, section, content, helpful, harmful}        │
│  ├─ _bullets: Dict[str, Bullet]                             │
│  ├─ _sections: Dict[str, List[str]]                         │
│  └─ as_prompt() → Returns ALL bullets formatted             │
└─────────────────────────────────────────────────────────────┘
```

### Available Infrastructure

✅ **Embedding API**: `any-llm` library has `embedding()` function
✅ **Bullet Metadata**: Already tracks helpful/harmful/neutral counts
✅ **Section Organization**: Bullets already grouped by section
✅ **Query Context**: Query string available in `_prepare_messages()`

---

## Proposed Architecture

### New Selection Flow

```
┌─────────────────────────────────────────────────────────────┐
│ query_processor.py (_prepare_messages)                      │
│  ├─ playbook = session.get_playbook()                       │
│  └─ playbook_context = playbook.as_context(                 │
│         query=query,            ✅ Query-specific            │
│         max_strategies=30       ✅ Limited to top-K          │
│      )                                                       │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Playbook.as_context(query, max_strategies)                  │
│  ├─ 1. Get or generate embeddings for all bullets           │
│  ├─ 2. Generate embedding for current query                 │
│  ├─ 3. Calculate hybrid scores (semantic + effectiveness)   │
│  ├─ 4. Select top-K bullets                                 │
│  └─ 5. Format selected bullets for context                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ BulletSelector (NEW component)                              │
│  ├─ EmbeddingCache: Store bullet embeddings                 │
│  ├─ semantic_similarity(query, bullet) → score              │
│  ├─ effectiveness_score(bullet) → score                     │
│  └─ hybrid_score(semantic, effectiveness) → final_score     │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Core Selection Infrastructure (Week 1)

**Goal**: Build basic bullet selection mechanism without embeddings

#### Tasks:
1. **Create BulletSelector class** (`swecli/core/context_management/selector.py`)
   - Effectiveness-based ranking (helpful/harmful ratio)
   - Top-K selection
   - Basic scoring algorithm

2. **Add `as_context()` method to Playbook**
   ```python
   def as_context(
       self,
       query: str,
       max_strategies: int = 30,
       use_semantic: bool = False  # Phase 2 feature
   ) -> str:
       """Select and format top-K most relevant bullets."""
   ```

3. **Update query_processor.py**
   - Replace `playbook.as_prompt()` with `playbook.as_context(query)`
   - Add configuration for max_strategies

#### Success Criteria:
- ✅ Playbook returns limited number of bullets (not all)
- ✅ Effectiveness scoring works (high helpful/harmful ratio prioritized)
- ✅ Existing tests pass
- ✅ No regression in chat functionality

---

### Phase 2: Semantic Similarity (Week 2)

**Goal**: Add embedding-based semantic matching

#### Tasks:
1. **Integrate any-llm embedding API**
   ```python
   from any_llm import embedding

   # Generate embedding for query
   query_embedding = embedding(query, model="text-embedding-3-small")
   ```

2. **Create EmbeddingCache**
   - Store bullet embeddings in memory
   - Lazy loading (compute on-demand)
   - Persistence (save to session data)

3. **Implement semantic similarity**
   ```python
   def semantic_similarity(query_emb, bullet_emb) -> float:
       """Cosine similarity between query and bullet."""
       return cosine_similarity(query_emb, bullet_emb)
   ```

4. **Update BulletSelector**
   - Add semantic scoring option
   - Combine with effectiveness scoring

#### Success Criteria:
- ✅ Embeddings generated for bullets on first use
- ✅ Embeddings cached and reused
- ✅ Semantic similarity working
- ✅ Query-specific bullet selection

---

### Phase 3: Hybrid Scoring Algorithm (Week 3)

**Goal**: Combine semantic and effectiveness scores optimally

#### Hybrid Score Formula:
```python
final_score = (
    α * semantic_similarity(query, bullet) +
    β * effectiveness_score(bullet) +
    γ * recency_score(bullet)
)

where:
  α = 0.6  # Weight for semantic relevance
  β = 0.3  # Weight for proven effectiveness
  γ = 0.1  # Weight for recent usage
```

#### Tasks:
1. **Effectiveness Score**
   ```python
   def effectiveness_score(bullet: Bullet) -> float:
       """Calculate effectiveness based on feedback."""
       total = bullet.helpful + bullet.harmful + bullet.neutral
       if total == 0:
           return 0.5  # Neutral for untested bullets
       return bullet.helpful / total
   ```

2. **Recency Score**
   ```python
   def recency_score(bullet: Bullet) -> float:
       """Prefer recently successful bullets."""
       days_old = (now - bullet.updated_at).days
       return 1.0 / (1.0 + days_old * 0.1)
   ```

3. **Configurable Weights**
   - Add to swecli config
   - Allow tuning via environment variables

#### Success Criteria:
- ✅ Hybrid scoring combines all three factors
- ✅ Weights are configurable
- ✅ Top-K selection based on hybrid scores
- ✅ A/B testing shows improvement

---

### Phase 4: Performance Optimization (Week 4)

**Goal**: Ensure system performs well at scale

#### Tasks:
1. **Embedding Caching Strategy**
   - In-memory cache (LRU with size limit)
   - Disk persistence (save with session)
   - Incremental updates (only new bullets)

2. **Batch Processing**
   ```python
   # Instead of embedding bullets one-by-one
   embeddings = embedding_batch([b.content for b in bullets])
   ```

3. **Lazy Loading**
   - Don't embed bullets until `as_context()` called
   - Skip embedding if max_strategies >= total bullets

4. **Performance Metrics**
   - Track selection time
   - Monitor cache hit rate
   - Measure token savings

#### Success Criteria:
- ✅ Selection completes in < 100ms for 1000 bullets
- ✅ Cache hit rate > 80% after warmup
- ✅ Token usage reduced by 50-80%
- ✅ No noticeable latency increase

---

### Phase 5: Evaluation & Tuning (Week 5)

**Goal**: Validate effectiveness and tune parameters

#### Tasks:
1. **Create Test Suite**
   - Unit tests for each scoring component
   - Integration tests for full selection flow
   - Benchmark tests for performance

2. **A/B Testing Framework**
   - Compare "all bullets" vs "selected bullets"
   - Track success rate of selected strategies
   - Measure user satisfaction

3. **Hyperparameter Tuning**
   - Find optimal α, β, γ weights
   - Determine best max_strategies value
   - Test different embedding models

4. **Monitoring Dashboard**
   - Selection stats (avg bullets selected)
   - Cache performance metrics
   - Cost savings visualization

#### Success Criteria:
- ✅ Test coverage > 85%
- ✅ Selection quality metrics defined
- ✅ Optimal parameters identified
- ✅ Production-ready monitoring

---

## Technical Specifications

### Data Structures

#### Extended Bullet
```python
@dataclass
class Bullet:
    id: str
    section: str
    content: str
    helpful: int = 0
    harmful: int = 0
    neutral: int = 0
    created_at: str
    updated_at: str

    # NEW: Embedding cache
    embedding: Optional[List[float]] = None
    embedding_model: Optional[str] = None
    embedding_updated_at: Optional[str] = None
```

#### BulletSelector
```python
class BulletSelector:
    def __init__(
        self,
        embedding_model: str = "text-embedding-3-small",
        weights: Dict[str, float] = None
    ):
        self.embedding_model = embedding_model
        self.weights = weights or {"semantic": 0.6, "effectiveness": 0.3, "recency": 0.1}
        self.embedding_cache = {}

    def select(
        self,
        query: str,
        bullets: List[Bullet],
        max_count: int = 30
    ) -> List[Bullet]:
        """Select top-K most relevant bullets."""

    def _calculate_score(
        self,
        query: str,
        bullet: Bullet
    ) -> float:
        """Calculate hybrid relevance score."""
```

### API Changes

#### playbook.py
```python
# NEW METHOD
def as_context(
    self,
    query: str,
    max_strategies: int = 30,
    use_semantic: bool = True,
    weights: Optional[Dict[str, float]] = None
) -> str:
    """Select and format top-K most relevant bullets for context.

    Args:
        query: Current user query for semantic matching
        max_strategies: Maximum number of bullets to include
        use_semantic: Whether to use embedding-based similarity
        weights: Custom scoring weights {semantic, effectiveness, recency}

    Returns:
        Formatted string with selected bullets
    """
```

#### query_processor.py
```python
# BEFORE
playbook_context = playbook.as_prompt()

# AFTER
playbook_context = playbook.as_context(
    query=query,
    max_strategies=self.config.get("max_playbook_strategies", 30)
)
```

### Configuration

#### config.yaml additions
```yaml
ace:
  playbook:
    max_strategies: 30
    embedding_model: "text-embedding-3-small"
    use_semantic_selection: true
    scoring_weights:
      semantic: 0.6
      effectiveness: 0.3
      recency: 0.1
    cache:
      enabled: true
      max_size: 1000
      ttl_hours: 24
```

---

## Testing Strategy

### Unit Tests

1. **BulletSelector Tests**
   - Test semantic similarity calculation
   - Test effectiveness scoring
   - Test hybrid score composition
   - Test top-K selection

2. **Playbook Tests**
   - Test `as_context()` returns correct count
   - Test fallback to `as_prompt()` if needed
   - Test caching behavior
   - Test edge cases (0 bullets, 1 bullet, etc.)

### Integration Tests

1. **End-to-End Selection**
   - Create playbook with diverse bullets
   - Query with different contexts
   - Verify relevant bullets selected

2. **Performance Tests**
   - Benchmark selection time
   - Test with 100, 500, 1000 bullets
   - Measure cache effectiveness

3. **Regression Tests**
   - Ensure existing chat functionality works
   - Verify ACE learning still works
   - Check session persistence

### A/B Testing Metrics

| Metric | Baseline (All Bullets) | Target (Selected) |
|--------|----------------------|------------------|
| Context tokens | ~5000 | ~1500 (70% reduction) |
| Relevance score | 0.65 | 0.80 (23% improvement) |
| Selection time | 0ms | <100ms |
| Success rate | 0.72 | 0.75 (4% improvement) |

---

## Migration Strategy

### Backward Compatibility

```python
def as_context(
    self,
    query: Optional[str] = None,
    max_strategies: Optional[int] = None,
    **kwargs
) -> str:
    """Backward-compatible selection method."""

    # If no query provided, fallback to all bullets
    if query is None:
        return self.as_prompt()

    # If max_strategies >= bullet count, no selection needed
    if max_strategies and max_strategies >= len(self._bullets):
        return self.as_prompt()

    # Otherwise, perform selection
    return self._select_and_format(query, max_strategies, **kwargs)
```

### Rollout Plan

1. **Phase 1**: Deploy with feature flag OFF
   - Code deployed but selection disabled
   - Monitor for any issues

2. **Phase 2**: Enable for internal testing (10% users)
   - Collect metrics
   - Compare with baseline

3. **Phase 3**: Gradual rollout (25% → 50% → 100%)
   - Monitor performance
   - Adjust weights if needed

4. **Phase 4**: Remove `as_prompt()` usage
   - Fully migrate to `as_context()`
   - Keep `as_prompt()` for debugging

---

## Risk Mitigation

### Risk 1: Embedding API Failures
**Mitigation**: Fallback to effectiveness-only scoring
```python
try:
    query_embedding = embedding(query)
except Exception:
    logger.warning("Embedding failed, using effectiveness-only")
    return self._select_by_effectiveness(max_strategies)
```

### Risk 2: Performance Degradation
**Mitigation**:
- Aggressive caching
- Lazy loading
- Batch embedding generation
- Async embedding computation

### Risk 3: Poor Selection Quality
**Mitigation**:
- A/B testing before full rollout
- Configurable weights for tuning
- Fallback to all bullets if selection fails
- Human-in-the-loop validation

### Risk 4: Cache Invalidation Issues
**Mitigation**:
- Version embeddings by model name
- Regenerate on bullet content change
- Clear cache on major updates

---

## Success Metrics

### Performance Metrics
- ✅ Selection latency < 100ms (p95)
- ✅ Cache hit rate > 80%
- ✅ Context token reduction > 50%

### Quality Metrics
- ✅ Relevance score improvement > 15%
- ✅ User satisfaction maintained or improved
- ✅ Success rate delta < -2% (within noise)

### Business Metrics
- ✅ API cost reduction > 40%
- ✅ Response time improvement > 10%
- ✅ Scalability: Support 1000+ bullet playbooks

---

## Next Steps

1. **Review this plan** with team
2. **Create Phase 1 tasks** in issue tracker
3. **Set up development environment**
4. **Create feature branch**: `feat/playbook-selection`
5. **Begin Phase 1 implementation**

---

## References

- [ACE Paper](https://arxiv.org/abs/2510.04618)
- [Current Playbook Implementation](../swecli/core/context_management/playbook.py)
- [Any-LLM Embedding API](../any-llm/src/any_llm/api.py)
- [ACE Complete Guide](../agentic-context-engine/docs/COMPLETE_GUIDE_TO_ACE.md)

---

**Last Updated**: 2025-01-12
**Status**: DRAFT - Pending Review
**Owner**: TBD
