import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { forecastsApi } from '../api/forecasts';
import ForecastGrid from '../components/forecasting/ForecastGrid';
import AdjustmentModal from '../components/forecasting/AdjustmentModal';

export default function ForecastDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [adjLineId, setAdjLineId] = useState<string | null>(null);

  const { data: forecast } = useQuery({
    queryKey: ['forecast', id],
    queryFn: () => forecastsApi.get(id!),
    enabled: !!id,
  });

  const { data: projection, isLoading } = useQuery({
    queryKey: ['forecast-projection', id],
    queryFn: () => forecastsApi.projection(id!),
    enabled: !!id,
  });

  if (!id) return null;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-primary">{forecast?.name ?? 'Forecast'}</h1>
          {forecast && (
            <p className="text-sm text-muted">
              Base year: {forecast.base_year} · {forecast.projection_years}-year projection
            </p>
          )}
        </div>
      </div>

      {isLoading ? (
        <div className="animate-pulse h-48 bg-muted-bg rounded" />
      ) : projection ? (
        <div className="bg-surface rounded-lg border border-line p-4">
          <ForecastGrid
            projection={projection}
            onAddAdjustment={(lineId) => setAdjLineId(lineId)}
          />
        </div>
      ) : null}

      {adjLineId && (
        <AdjustmentModal
          open
          onClose={() => setAdjLineId(null)}
          forecastId={id}
          lineId={adjLineId}
        />
      )}
    </div>
  );
}
