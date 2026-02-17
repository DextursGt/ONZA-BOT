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
      max_memory_restart: '700M'  // Increased for bot + dashboard
    }
  ]
};
