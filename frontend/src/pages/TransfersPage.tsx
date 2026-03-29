import TransferList from '../components/transfers/TransferList';

export default function TransfersPage() {
  return (
    <div className="max-w-3xl space-y-4">
      <h1 className="text-xl font-bold text-primary">Transfers</h1>
      <TransferList />
    </div>
  );
}
