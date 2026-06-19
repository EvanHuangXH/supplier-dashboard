export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'POST only' });

  const token = process.env.GH_PAT;
  if (!token) return res.status(500).json({ error: 'GH_PAT not configured' });

  try {
    const response = await fetch(
      'https://api.github.com/repos/EvanHuangXH/supplier-dashboard/actions/workflows/scrape.yml/dispatches',
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Accept': 'application/vnd.github+json',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ ref: 'main' }),
      }
    );

    if (response.ok) {
      return res.json({ success: true, message: '抓取已触发，约5分钟后开始运行' });
    } else {
      const err = await response.text();
      return res.status(response.status).json({ error: err });
    }
  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
}
