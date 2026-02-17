module.exports = {
  apps: [
    {
      name: 'ONZA-BOT',
      script: '/root/ONZA-BOT/main.py',
      interpreter: 'python3',
      cwd: '/root/ONZA-BOT',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M'
    },
    {
      name: 'ONZA-DASHBOARD',
      script: 'uvicorn',
      args: 'dashboard.app:app --host 0.0.0.0 --port 8000',
      interpreter: 'python3',
      cwd: '/root/ONZA-BOT',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '200M'
    }
  ]
};
