import { Link } from 'react-router-dom';
import RegisterForm from '../components/auth/RegisterForm';

export default function RegisterPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-canvas">
      <div className="bg-surface rounded-lg shadow-sm border border-line p-8 w-full max-w-sm">
        <h1 className="text-2xl font-bold mb-6 text-center text-primary">Create Account</h1>
        <RegisterForm />
        <p className="mt-4 text-center text-sm text-muted">
          Already have an account?{' '}
          <Link to="/login" className="text-blue-600 hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
