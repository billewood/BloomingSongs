/**
 * Health check endpoint for the frontend
 */

export default async function handler(req, res) {
  const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
  
  try {
    const response = await fetch(`${backendUrl}/api/health`);
    const data = await response.json();
    
    return res.status(200).json({
      frontend: 'healthy',
      backend: data.status || 'unknown',
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    return res.status(200).json({
      frontend: 'healthy',
      backend: 'unreachable',
      error: error.message,
      timestamp: new Date().toISOString(),
    });
  }
}
