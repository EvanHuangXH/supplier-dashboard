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
    }

    // Map GitHub's raw error to an actionable message
    let detail = '';
    try {
      const data = await response.json();
      detail = data.message || JSON.stringify(data);
    } catch {
      detail = await response.text();
    }

    let message = detail;
    if (response.status === 401) {
      message = 'GitHub 访问令牌无效或已过期，请更新 Vercel 中的 GH_PAT 环境变量后重新部署';
    } else if (response.status === 403) {
      message = 'GitHub 访问令牌权限不足，需具备 repo 或 workflow 权限';
    } else if (response.status === 404) {
      message = '未找到工作流 scrape.yml，请确认其位于 main 分支';
    }
    return res.status(response.status).json({ error: message });
  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
}
