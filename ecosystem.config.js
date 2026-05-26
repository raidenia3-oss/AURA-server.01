module.exports = {
  apps: [
    {
      name: 'aura-servidor-ame',
      script: 'servidor_ame.py',
      cwd: '/home/user/AURA/AME_Core',
      interpreter: '/home/user/AURA/env/bin/python',
      instances: 1,
      exec_mode: 'fork',
      watch: false,
      max_memory_restart: '1G',
      env: {
        FLASK_ENV: 'production',
        PYTHONUNBUFFERED: 1
      },
      error_file: './logs/aura-error.log',
      out_file: './logs/aura-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true
    }
  ]
};
