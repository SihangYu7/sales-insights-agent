import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { getSalesSummary, getProducts } from '../services/api';

interface SalesSummary {
  total_sales: number;
  total_transactions: number;
  by_region: Array<{ region: string; total: number; count: number }>;
  by_category: Array<{ category: string; total: number; count: number }>;
  top_products: Array<{ name: string; total: number; units_sold: number }>;
}

interface Product {
  id: number;
  name: string;
  category: string;
  price: number;
}

const Dashboard = () => {
  const { user, logout } = useAuth();
  const [summary, setSummary] = useState<SalesSummary | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [summaryData, productsData] = await Promise.all([
          getSalesSummary(),
          getProducts(),
        ]);
        setSummary(summaryData);
        setProducts(productsData.products);
      } catch (err) {
        setError('Failed to load data');
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, []);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">Sales Dashboard</h1>
          <div className="flex items-center space-x-4">
            <Link
              to="/chat"
              className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition"
            >
              AI Chat
            </Link>
            <span className="text-gray-600">{user?.email}</span>
            <button
              onClick={logout}
              className="text-gray-500 hover:text-gray-700"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-md mb-6">
            {error}
          </div>
        )}

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-500">Total Sales</h3>
            <p className="mt-2 text-3xl font-bold text-gray-900">
              ${summary?.total_sales.toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </p>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-500">Transactions</h3>
            <p className="mt-2 text-3xl font-bold text-gray-900">
              {summary?.total_transactions}
            </p>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-500">Products</h3>
            <p className="mt-2 text-3xl font-bold text-gray-900">{products.length}</p>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-500">Avg per Transaction</h3>
            <p className="mt-2 text-3xl font-bold text-gray-900">
              ${summary ? (summary.total_sales / summary.total_transactions).toFixed(2) : '0'}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Sales by Region */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Sales by Region</h2>
            <div className="space-y-3">
              {summary?.by_region.map((region) => (
                <div key={region.region} className="flex items-center justify-between">
                  <span className="text-gray-600">{region.region}</span>
                  <div className="flex items-center space-x-4">
                    <span className="text-sm text-gray-500">{region.count} sales</span>
                    <span className="font-medium text-gray-900">
                      ${region.total.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Sales by Category */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Sales by Category</h2>
            <div className="space-y-3">
              {summary?.by_category.map((cat) => (
                <div key={cat.category} className="flex items-center justify-between">
                  <span className="text-gray-600">{cat.category}</span>
                  <div className="flex items-center space-x-4">
                    <span className="text-sm text-gray-500">{cat.count} sales</span>
                    <span className="font-medium text-gray-900">
                      ${cat.total.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Top Products */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Top Products</h2>
            <div className="space-y-3">
              {summary?.top_products.map((product, index) => (
                <div key={product.name} className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <span className="bg-blue-100 text-blue-800 text-xs font-medium px-2.5 py-0.5 rounded">
                      #{index + 1}
                    </span>
                    <span className="text-gray-600">{product.name}</span>
                  </div>
                  <span className="font-medium text-gray-900">
                    ${product.total.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Products List */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">All Products</h2>
            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-2 text-sm font-medium text-gray-500">Name</th>
                    <th className="text-left py-2 text-sm font-medium text-gray-500">Category</th>
                    <th className="text-right py-2 text-sm font-medium text-gray-500">Price</th>
                  </tr>
                </thead>
                <tbody>
                  {products.map((product) => (
                    <tr key={product.id} className="border-b last:border-b-0">
                      <td className="py-2 text-sm text-gray-900">{product.name}</td>
                      <td className="py-2 text-sm text-gray-500">{product.category}</td>
                      <td className="py-2 text-sm text-gray-900 text-right">
                        ${product.price.toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
