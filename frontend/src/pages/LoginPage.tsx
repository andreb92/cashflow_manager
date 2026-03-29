import { Link } from 'react-router-dom';
import LoginForm from '../components/auth/LoginForm';

export default function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-canvas">
      <div className="bg-surface rounded-lg shadow-sm border border-line p-8 w-full max-w-sm">
        <h1 className="text-2xl font-bold mb-6 text-center text-primary">Sign in</h1>
        <LoginForm />
        <p className="mt-4 text-center text-sm text-muted">
          Don't have an account?{' '}
          <Link to="/register" className="text-blue-600 hover:underline">
            Register
          </Link>
        </p>
      </div>
    </div>
  );
}
