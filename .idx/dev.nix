{ pkgs, ... }: {
  channel = "stable-23.11";

  packages = [
    pkgs.python311
  ];

  idx.extensions = [
    "ms-python.python"
  ];

  idx.previews = {
    enable = true;
    previews = {
      web = {
        command = ["/bin/bash" "-c" "source ~/.venv/bin/activate && uvicorn index:app --host 0.0.0.0 --port $PORT --reload"];
        manager = "web";
      };
    };
  };

  idx.workspace.onCreate = {
    install-deps = "python -m venv ~/.venv && source ~/.venv/bin/activate && pip install fastapi uvicorn requests upstash-vector upstash-redis duckduckgo-search beautifulsoup4 lxml";
  };
}