import { useParams, Link } from 'react-router-dom';
import { ArrowLeftIcon, StarIcon, DocumentTextIcon, FolderIcon, CheckCircleIcon, ExclamationCircleIcon, ArrowPathIcon, ClockIcon } from '@heroicons/react/24/outline';
import { DocumentationViewer } from './DocumentationViewer';
import { Repository } from './RepositoryExplorer';

// Mock function to get repository by name
const getRepositoryByName = (name: string): Repository | null => {
  const mockRepositories: Repository[] = [
    {
      id: '1',
      name: 'react',
      fullName: 'facebook/react',
      description: 'A declarative, efficient, and flexible JavaScript library for building user interfaces.',
      language: 'JavaScript',
      stars: 220000,
      lastIndexed: '2 hours ago',
      status: 'indexed',
      files: 3456,
      docsFound: 234
    },
    {
      id: '2',
      name: 'swe-cli',
      fullName: 'swe-cli/swe-cli',
      description: 'Software Engineering CLI with AI-powered coding assistance.',
      language: 'Python',
      stars: 1250,
      lastIndexed: '1 day ago',
      status: 'indexed',
      files: 892,
      docsFound: 67,
      localPath: '/Users/quocnghi/codes/swe-cli'
    },
    {
      id: '3',
      name: 'next.js',
      fullName: 'vercel/next.js',
      description: 'The React Framework for Production.',
      language: 'TypeScript',
      stars: 125000,
      lastIndexed: '3 days ago',
      status: 'error',
      files: 2341,
      docsFound: 0
    }
  ];

  return mockRepositories.find(repo => repo.name === name) || null;
};

// Language color mapping
const languageColors: Record<string, string> = {
  'JavaScript': 'bg-yellow-400',
  'TypeScript': 'bg-blue-400',
  'Python': 'bg-green-400',
  'Java': 'bg-red-400',
  'C++': 'bg-purple-400',
  'Go': 'bg-cyan-400',
  'Rust': 'bg-orange-400',
  'Ruby': 'bg-red-500',
  'PHP': 'bg-indigo-400',
  'Swift': 'bg-orange-500',
  'default': 'bg-gray-400'
};

interface RepositoryDetailPageProps {
  searchQuery?: string;
}

export function RepositoryDetailPage({ searchQuery = '' }: RepositoryDetailPageProps) {
  const { repoName } = useParams<{ repoName: string }>();
  const repository = getRepositoryByName(repoName || '');

  const getStatusIcon = (status: Repository['status']) => {
    switch (status) {
      case 'indexed':
        return <CheckCircleIcon className="w-5 h-5 text-green-500" />;
      case 'indexing':
        return <ArrowPathIcon className="w-5 h-5 text-blue-500 animate-spin" />;
      case 'error':
        return <ExclamationCircleIcon className="w-5 h-5 text-red-500" />;
    }
  };

  const getStatusText = (status: Repository['status']) => {
    switch (status) {
      case 'indexed':
        return 'Indexed';
      case 'indexing':
        return 'Indexing...';
      case 'error':
        return 'Error';
    }
  };

  const formatNumber = (num: number) => {
    if (num >= 1000) {
      return `${(num / 1000).toFixed(1)}k`;
    }
    return num.toString();
  };

  if (!repository) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-20 h-20 mx-auto mb-6 bg-gray-100 rounded-full flex items-center justify-center">
            <FolderIcon className="w-10 h-10 text-gray-400" />
          </div>
          <h3 className="text-xl font-semibold text-gray-900 mb-2">Repository Not Found</h3>
          <p className="text-gray-600 mb-6">The repository "{repoName}" could not be found.</p>
          <Link
            to="/codewiki"
            className="inline-flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white font-medium rounded-lg transition-colors"
          >
            <ArrowLeftIcon className="w-4 h-4" />
            Back to CodeWiki
          </Link>
        </div>
      </div>
    );
  }

  const languageColor = languageColors[repository.language] || languageColors.default;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header with Repository Info */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-6">
          {/* Breadcrumb Navigation */}
          <nav className="flex items-center gap-2 text-sm text-gray-500 mb-6">
            <Link to="/codewiki" className="hover:text-gray-700 transition-colors">
              CodeWiki
            </Link>
            <span>/</span>
            <span className="text-gray-900 font-medium">{repository.name}</span>
          </nav>

          {/* Repository Header */}
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-4">
              {/* Repository Icon */}
              <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-blue-600 rounded-xl flex items-center justify-center shadow-lg">
                <FolderIcon className="w-8 h-8 text-white" />
              </div>

              {/* Repository Info */}
              <div>
                <h1 className="text-3xl font-bold text-gray-900 mb-1">{repository.name}</h1>
                <p className="text-gray-600 text-lg mb-3">{repository.fullName}</p>
                <p className="text-gray-700 max-w-3xl">{repository.description}</p>

                {/* Language and Status */}
                <div className="flex items-center gap-4 mt-4">
                  <div className="flex items-center gap-2">
                    <div className={`w-4 h-4 rounded-full ${languageColor}`} />
                    <span className="font-medium text-gray-900">{repository.language}</span>
                  </div>

                  <div className="flex items-center gap-2 px-3 py-1 bg-gray-100 rounded-full">
                    {getStatusIcon(repository.status)}
                    <span className="text-sm font-medium text-gray-700">{getStatusText(repository.status)}</span>
                  </div>

                  {repository.localPath && (
                    <span className="px-3 py-1 bg-blue-100 text-blue-700 text-sm rounded-full font-medium">
                      Local Repository
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Back Button */}
            <Link
              to="/codewiki"
              className="flex items-center gap-2 px-4 py-2 text-gray-700 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ArrowLeftIcon className="w-4 h-4" />
              Back to Overview
            </Link>
          </div>
        </div>
      </div>

      {/* Stats Bar */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="grid grid-cols-4 gap-8">
            <div className="text-center">
              <div className="flex items-center justify-center gap-2 text-gray-500 mb-2">
                <StarIcon className="w-5 h-5" />
              </div>
              <div className="text-xl font-bold text-gray-900">{formatNumber(repository.stars)}</div>
              <div className="text-sm text-gray-500">Stars</div>
            </div>

            <div className="text-center">
              <div className="flex items-center justify-center gap-2 text-gray-500 mb-2">
                <DocumentTextIcon className="w-5 h-5" />
              </div>
              <div className="text-xl font-bold text-gray-900">{repository.files.toLocaleString()}</div>
              <div className="text-sm text-gray-500">Files</div>
            </div>

            <div className="text-center">
              <div className="flex items-center justify-center gap-2 text-gray-500 mb-2">
                <DocumentTextIcon className="w-5 h-5" />
              </div>
              <div className="text-xl font-bold text-gray-900">{repository.docsFound}</div>
              <div className="text-sm text-gray-500">Documents</div>
            </div>

            <div className="text-center">
              <div className="flex items-center justify-center gap-2 text-gray-500 mb-2">
                <ClockIcon className="w-5 h-5" />
              </div>
              <div className="text-xl font-bold text-gray-900">{repository.lastIndexed}</div>
              <div className="text-sm text-gray-500">Last Indexed</div>
            </div>
          </div>
        </div>
      </div>

      {/* Documentation Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        <DocumentationViewer
          selectedRepo={repository.id}
          searchQuery={searchQuery}
          onIndexingChange={() => {}}
        />
      </div>
    </div>
  );
}