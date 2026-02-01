import { useState, useEffect } from 'react';
import Head from 'next/head';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const REGIONS = [
  { code: 'US-CA', name: 'California' },
  { code: 'US-NY', name: 'New York' },
  { code: 'US-TX', name: 'Texas' },
  { code: 'US-FL', name: 'Florida' },
];

const TIME_PERIODS = [
  { value: 3, label: 'Last 3 days' },
  { value: 7, label: 'Last 7 days' },
  { value: 14, label: 'Last 14 days' },
  { value: 30, label: 'Last 30 days' },
];

const DATA_SOURCES = [
  { value: 'all', label: 'All Sources' },
  { value: 'ebird', label: 'eBird Only' },
  { value: 'inaturalist', label: 'iNaturalist Only' },
];

export default function Home() {
  const [activeTab, setActiveTab] = useState('current');
  const [regionCode, setRegionCode] = useState('US-CA');
  const [days, setDays] = useState(7);
  const [dataSource, setDataSource] = useState('all');
  const [currentBirds, setCurrentBirds] = useState([]);
  const [trends, setTrends] = useState([]);
  const [historicalData, setHistoricalData] = useState(null);
  const [sources, setSources] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchData();
  }, [activeTab, regionCode, days, dataSource]);

  const fetchData = async () => {
    setLoading(true);
    setError(null);

    try {
      let url;
      const sourceParam = dataSource !== 'all' ? `&source=${dataSource}` : '';
      
      if (activeTab === 'current') {
        url = `/api/birds/current?region_code=${regionCode}&days=${days}&limit=50${sourceParam}`;
      } else if (activeTab === 'trends') {
        url = `/api/birds/trends?region_code=${regionCode}&days=${days}&limit=50`;
      } else if (activeTab === 'historical') {
        url = `/api/birds/historical?region_code=${regionCode}&days=90${sourceParam}`;
      }

      const response = await fetch(url);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to fetch data');
      }

      if (activeTab === 'current') {
        setCurrentBirds(data.birds || []);
        setSources(data.sources || null);
      } else if (activeTab === 'trends') {
        setTrends(data || []);
      } else if (activeTab === 'historical') {
        setHistoricalData(data);
        setSources(data.sources || null);
      }
    } catch (err) {
      setError(err.message);
      console.error('Error fetching data:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatHistoricalChartData = () => {
    if (!historicalData || !historicalData.data) return [];

    const speciesTotals = {};
    Object.values(historicalData.data).forEach(dayData => {
      dayData.forEach(bird => {
        if (!speciesTotals[bird.species_code]) {
          speciesTotals[bird.species_code] = {
            species_code: bird.species_code,
            common_name: bird.common_name,
            total: 0
          };
        }
        speciesTotals[bird.species_code].total += bird.observation_count || bird.count || 0;
      });
    });

    const topSpecies = Object.values(speciesTotals)
      .sort((a, b) => b.total - a.total)
      .slice(0, 5)
      .map(s => s.species_code);

    const chartData = [];
    const dates = Object.keys(historicalData.data).sort();

    dates.forEach(date => {
      const dayData = historicalData.data[date];
      const dayEntry = { date: new Date(date).toLocaleDateString() };

      topSpecies.forEach(speciesCode => {
        const bird = dayData.find(b => b.species_code === speciesCode);
        const speciesName = speciesTotals[speciesCode]?.common_name || speciesCode;
        dayEntry[speciesName] = bird?.observation_count || bird?.count || 0;
      });

      chartData.push(dayEntry);
    });

    return chartData;
  };

  const getTrendBadgeClass = (direction) => {
    switch (direction) {
      case 'rising':
        return 'bg-green-100 text-green-800';
      case 'falling':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-blue-100 text-blue-800';
    }
  };

  return (
    <>
      <Head>
        <title>BloomingSongs - Bird Singing Activity Tracker</title>
        <meta name="description" content="Track which birds are singing in your area" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <main className="min-h-screen py-8 px-4">
        <div className="max-w-6xl mx-auto">
          {/* Header */}
          <header className="text-center mb-8">
            <h1 className="text-4xl md:text-5xl font-bold text-white mb-2 drop-shadow-lg">
              🐦 BloomingSongs
            </h1>
            <p className="text-xl text-white/90">
              Track which birds are singing in your area
            </p>
          </header>

          {/* Main Card */}
          <div className="bg-white rounded-2xl shadow-xl p-6 md:p-8">
            {/* Controls */}
            <div className="flex flex-wrap gap-4 mb-6">
              <select
                value={regionCode}
                onChange={(e) => setRegionCode(e.target.value)}
                className="px-4 py-2 border-2 border-gray-200 rounded-lg focus:border-primary-500 focus:outline-none"
              >
                {REGIONS.map(region => (
                  <option key={region.code} value={region.code}>
                    {region.name}
                  </option>
                ))}
              </select>

              {activeTab !== 'historical' && (
                <select
                  value={days}
                  onChange={(e) => setDays(Number(e.target.value))}
                  className="px-4 py-2 border-2 border-gray-200 rounded-lg focus:border-primary-500 focus:outline-none"
                >
                  {TIME_PERIODS.map(period => (
                    <option key={period.value} value={period.value}>
                      {period.label}
                    </option>
                  ))}
                </select>
              )}

              <select
                value={dataSource}
                onChange={(e) => setDataSource(e.target.value)}
                className="px-4 py-2 border-2 border-gray-200 rounded-lg focus:border-primary-500 focus:outline-none"
              >
                {DATA_SOURCES.map(source => (
                  <option key={source.value} value={source.value}>
                    {source.label}
                  </option>
                ))}
              </select>

              <button
                onClick={fetchData}
                className="px-6 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
              >
                Refresh
              </button>
            </div>

            {/* Source Stats */}
            {sources && (
              <div className="flex gap-4 mb-6 text-sm">
                <div className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full">
                  eBird: {sources.ebird?.toLocaleString() || 0}
                </div>
                <div className="px-3 py-1 bg-green-100 text-green-800 rounded-full">
                  iNaturalist: {sources.inaturalist?.toLocaleString() || 0}
                </div>
                <div className="px-3 py-1 bg-gray-100 text-gray-800 rounded-full">
                  Total: {sources.total?.toLocaleString() || 0}
                </div>
              </div>
            )}

            {/* Tabs */}
            <div className="flex border-b border-gray-200 mb-6">
              {['current', 'trends', 'historical'].map(tab => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-6 py-3 font-medium transition-colors ${
                    activeTab === tab
                      ? 'text-primary-600 border-b-2 border-primary-600'
                      : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  {tab === 'current' ? 'Current Activity' :
                   tab === 'trends' ? 'Trends' : 'Historical'}
                </button>
              ))}
            </div>

            {/* Error State */}
            {error && (
              <div className="bg-red-50 text-red-700 p-4 rounded-lg mb-6">
                Error: {error}
              </div>
            )}

            {/* Loading State */}
            {loading && (
              <div className="text-center py-12 text-gray-500">
                Loading...
              </div>
            )}

            {/* Current Activity Tab */}
            {!loading && activeTab === 'current' && (
              <div>
                <h2 className="text-2xl font-bold text-gray-800 mb-4">
                  Most Active Birds ({REGIONS.find(r => r.code === regionCode)?.name})
                </h2>
                <div className="space-y-3">
                  {currentBirds.length === 0 ? (
                    <p className="text-gray-500 py-8 text-center">
                      No data available. Make sure the backend is running and data has been fetched.
                    </p>
                  ) : (
                    currentBirds.map((bird, idx) => (
                      <div
                        key={bird.species_code || idx}
                        className="flex justify-between items-center p-4 bg-gray-50 rounded-lg border-l-4 border-primary-500 hover:translate-x-1 transition-transform"
                      >
                        <div>
                          <div className="font-semibold text-gray-800">{bird.common_name}</div>
                          <div className="text-sm text-gray-500 italic">{bird.scientific_name}</div>
                        </div>
                        <div className="text-lg font-bold text-primary-600">
                          {bird.observation_count} observations
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}

            {/* Trends Tab */}
            {!loading && activeTab === 'trends' && (
              <div>
                <h2 className="text-2xl font-bold text-gray-800 mb-4">
                  Bird Activity Trends
                </h2>
                <div className="space-y-3">
                  {trends.length === 0 ? (
                    <p className="text-gray-500 py-8 text-center">
                      No trend data available.
                    </p>
                  ) : (
                    trends.map((trend, idx) => (
                      <div
                        key={trend.species_code || idx}
                        className="flex justify-between items-center p-4 bg-gray-50 rounded-lg border-l-4 border-primary-500"
                      >
                        <div>
                          <div className="font-semibold text-gray-800">
                            {trend.common_name}
                            <span className={`ml-2 px-2 py-1 rounded-full text-xs font-semibold ${getTrendBadgeClass(trend.trend_direction)}`}>
                              {trend.trend_direction}
                            </span>
                          </div>
                          <div className="text-sm text-gray-500 mt-1">
                            {trend.previous_count} → {trend.current_count} observations
                          </div>
                        </div>
                        <div className={`text-lg font-bold ${trend.change_percent > 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {trend.change_percent > 0 ? '+' : ''}{trend.change_percent.toFixed(1)}%
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}

            {/* Historical Tab */}
            {!loading && activeTab === 'historical' && (
              <div>
                <h2 className="text-2xl font-bold text-gray-800 mb-4">
                  Historical Trends (Last 90 Days)
                </h2>
                {historicalData && historicalData.data && Object.keys(historicalData.data).length > 0 ? (
                  <div className="h-96">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={formatHistoricalChartData()}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="date" />
                        <YAxis />
                        <Tooltip />
                        <Legend />
                        {formatHistoricalChartData().length > 0 &&
                          Object.keys(formatHistoricalChartData()[0])
                            .filter(key => key !== 'date')
                            .map((species, idx) => (
                              <Line
                                key={species}
                                type="monotone"
                                dataKey={species}
                                stroke={`hsl(${idx * 60}, 70%, 50%)`}
                                strokeWidth={2}
                              />
                            ))}
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <p className="text-gray-500 py-8 text-center">
                    No historical data available.
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Footer */}
          <footer className="text-center mt-8 text-white/80">
            <p>
              Data powered by{' '}
              <a href="https://ebird.org" target="_blank" rel="noopener noreferrer" className="underline hover:text-white">
                eBird
              </a>
              {' '}and{' '}
              <a href="https://inaturalist.org" target="_blank" rel="noopener noreferrer" className="underline hover:text-white">
                iNaturalist
              </a>
            </p>
          </footer>
        </div>
      </main>
    </>
  );
}
