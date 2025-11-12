import { useParams, Link } from 'react-router-dom';
import { ArrowLeftIcon, FolderIcon, CheckCircleIcon, ExclamationCircleIcon, ArrowPathIcon } from '@heroicons/react/24/outline';
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


interface RepositoryDetailPageProps {
  searchQuery?: string;
}

export function RepositoryDetailPage({ searchQuery = '' }: RepositoryDetailPageProps) {
  const { repoName } = useParams<{ repoName: string }>();
  const repository = getRepositoryByName(repoName || '');

  const getStatusIcon = (status: Repository['status']) => {
    switch (status) {
      case 'indexed':
        return <CheckCircleIcon className="w-4 h-4 text-green-500" />;
      case 'indexing':
        return <ArrowPathIcon className="w-4 h-4 text-blue-500 animate-spin" />;
      case 'error':
        return <ExclamationCircleIcon className="w-4 h-4 text-red-500" />;
    }
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

  
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Simplified Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          {/* Breadcrumb Navigation */}
          <nav className="flex items-center gap-2 text-sm text-gray-500 mb-4">
            <Link to="/codewiki" className="hover:text-gray-700 transition-colors">
              CodeWiki
            </Link>
            <span>/</span>
            <span className="text-gray-900 font-medium">{repository.name}</span>
          </nav>

          {/* Repository Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {/* Repository Icon */}
              <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-blue-600 rounded-lg flex items-center justify-center">
                <FolderIcon className="w-5 h-5 text-white" />
              </div>

              {/* Repository Info */}
              <div>
                <h1 className="text-2xl font-bold text-gray-900">{repository.name}</h1>
                <p className="text-gray-600">{repository.fullName}</p>
              </div>
            </div>

            {/* Status and Back Button */}
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-100 rounded-full">
                {getStatusIcon(repository.status)}
                <span className="text-sm font-medium text-gray-700 capitalize">{repository.status}</span>
              </div>

              <Link
                to="/codewiki"
                className="flex items-center gap-2 px-4 py-2 text-gray-700 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <ArrowLeftIcon className="w-4 h-4" />
                Back
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Documentation Content - Full Width */}
      <DocumentationViewer
        selectedRepo={repository.id}
        searchQuery={searchQuery}
        onIndexingChange={() => {}}
      />
    </div>
  );
}