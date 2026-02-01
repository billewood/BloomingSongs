/**
 * API Route: Proxy to Python backend
 * 
 * This route proxies all /api/birds/* requests to the Python backend.
 * Similar to Life Risk Estimator's /api/calculate route.
 */

export default async function handler(req, res) {
  const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
  const { path } = req.query;
  const apiPath = Array.isArray(path) ? path.join('/') : path;
  
  // Build the full URL with query parameters
  const url = new URL(`${backendUrl}/api/birds/${apiPath}`);
  
  // Add query parameters
  Object.entries(req.query).forEach(([key, value]) => {
    if (key !== 'path') {
      url.searchParams.append(key, value);
    }
  });

  try {
    const response = await fetch(url.toString(), {
      method: req.method,
      headers: {
        'Content-Type': 'application/json',
      },
      body: req.method !== 'GET' ? JSON.stringify(req.body) : undefined,
    });

    const data = await response.json();
    
    if (!response.ok) {
      return res.status(response.status).json(data);
    }

    return res.status(200).json(data);
  } catch (error) {
    console.error('Backend API error:', error);
    return res.status(500).json({ 
      error: 'Failed to connect to backend',
      details: error.message 
    });
  }
}
