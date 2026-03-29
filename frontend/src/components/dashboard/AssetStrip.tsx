import type { Asset } from '../../types/api';
import { fmt } from '../../utils/format';

interface Props { assets: Asset[] | undefined; isLoading: boolean; }

export default function AssetStrip({ assets, isLoading }: Props) {
  if (isLoading) return <div className="bg-surface rounded-lg border border-line p-6 animate-pulse h-20" />;
  return (
    <div className="bg-surface rounded-lg border border-line p-4 flex flex-wrap gap-4">
      {(assets ?? []).map((a) => (
        <div key={`${a.asset_type}-${a.asset_name}`} className="flex flex-col">
          <span className="text-xs text-muted">{a.asset_name}</span>
          <span className="font-semibold text-primary">€{fmt(a.final_amount)}</span>
          {a.manual_override !== null && (
            <span className="text-xs text-yellow-600">manual</span>
          )}
        </div>
      ))}
    </div>
  );
}
