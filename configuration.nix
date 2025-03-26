# This is just here for testing purposes
{ config, pkgs, lib, ... }:

{

  # Bootloader and kernel configuration
  boot = {
    loader = {
      systemd-boot.enable = true;
      efi.canTouchEfiVariables = true;
      grub = {
        enable = false;
        device = "nodev";
        efiSupport = true;
        useOSProber = true;
      };

    };
    kernelPackages = pkgs.linuxPackages_latest;
    kernelParams = [ "quiet" "splash" ];
    kernelModules = [ "kvm-intel" "wireguard" ];
    tmp.cleanOnBoot = true;
  };

  # Networking configuration
  networking = {
    hostName = "nixos-server";
    domain = "example.com";
    networkmanager.enable = true;
    useDHCP = false;
    interfaces = {
      enp0s3 = {
        ipv4.addresses = [{
          address = "192.168.1.100";
          prefixLength = 24;
        }];
        useDHCP = false;
      };
    };
    defaultGateway = "192.168.1.1";
    nameservers = [ "1.1.1.1" "8.8.8.8" ];
    firewall = {
      enable = true;
      allowedTCPPorts = [ 22 80 443 5432 8080 9090 3000 ];
      allowedUDPPorts = [ 53 ];
      allowPing = true;
    };
  };

  # Time zone and locale settings
  time.timeZone = "UTC";
  i18n.defaultLocale = "en_US.UTF-8";
  i18n.extraLocaleSettings = {
    LC_ADDRESS = "en_US.UTF-8";
    LC_IDENTIFICATION = "en_US.UTF-8";
    LC_MEASUREMENT = "en_US.UTF-8";
    LC_MONETARY = "en_US.UTF-8";
    LC_NAME = "en_US.UTF-8";
    LC_NUMERIC = "en_US.UTF-8";
    LC_PAPER = "en_US.UTF-8";
    LC_TELEPHONE = "en_US.UTF-8";
    LC_TIME = "en_US.UTF-8";
  };

  # Enable basic services
  services = {
    # SSH server
    openssh = {
      enable = true;
      permitRootLogin = "no";
      passwordAuthentication = false;
      ports = [ 22 ];
      extraConfig = ''
        AllowGroups wheel admins
        X11Forwarding no
        MaxAuthTries 5
      '';
    };

    # Web server (Nginx)
    nginx = {
      enable = true;
      recommendedGzipSettings = true;
      recommendedOptimisation = true;
      recommendedProxySettings = true;
      recommendedTlsSettings = true;

      virtualHosts = {
        "example.com" = {
          enableACME = true;
          forceSSL = true;
          root = "/var/www/example.com";
          locations."/" = {
            index = "index.html";
          };
          locations."/api/" = {
            proxyPass = "http://127.0.0.1:3000";
            extraConfig = ''
              proxy_http_version 1.1;
              proxy_set_header Upgrade $http_upgrade;
              proxy_set_header Connection "upgrade";
            '';
          };
        };
        "dashboard.example.com" = {
          enableACME = true;
          forceSSL = true;
          locations."/" = {
            proxyPass = "http://127.0.0.1:3000";
          };
        };
      };
    };

    # Database server (PostgreSQL)
    postgresql = {
      enable = true;
      package = pkgs.postgresql_14;
      enableTCPIP = true;
      authentication = lib.mkOverride 10 ''
        local all all trust
        host all all 127.0.0.1/32 trust
        host all all ::1/128 trust
        host replication replicator 192.168.1.0/24 md5
      '';
      initialScript = pkgs.writeText "backend-initScript" ''
        CREATE ROLE admin WITH LOGIN PASSWORD 'admin' CREATEDB;
        CREATE DATABASE app;
        GRANT ALL PRIVILEGES ON DATABASE app TO admin;
        
        CREATE ROLE app_user WITH LOGIN PASSWORD 'app_password';
        GRANT CONNECT ON DATABASE app TO app_user;
      '';
      settings = {
        max_connections = 100;
        shared_buffers = "2GB";
        effective_cache_size = "6GB";
        maintenance_work_mem = "512MB";
        checkpoint_completion_target = 0.9;
        wal_buffers = "16MB";
        default_statistics_target = 100;
        random_page_cost = 1.1;
        effective_io_concurrency = 200;
        work_mem = "52428kB";
        min_wal_size = "1GB";
        max_wal_size = "4GB";
      };
    };

    # Redis cache
    redis = {
      enable = true;
      package = pkgs.redis;
      settings = {
        bind = "127.0.0.1";
        port = 6379;
        maxmemory = "512mb";
        maxmemory-policy = "allkeys-lru";
      };
    };

    # Monitoring with Prometheus and Grafana
    prometheus = {
      enable = true;
      port = 9090;
      exporters = {
        node = {
          enable = true;
          enabledCollectors = [ "systemd" ];
          port = 9100;
        };
        nginx = {
          enable = true;
          port = 9113;
        };
        postgres = {
          enable = true;
          port = 9187;
          runAsLocalSuperUser = true;
        };
        redis = {
          enable = true;
          port = 9121;
        };
      };
      scrapeConfigs = [
        {
          job_name = "node";
          static_configs = [{
            targets = [ "localhost:9100" ];
          }];
        }
        {
          job_name = "nginx";
          static_configs = [{
            targets = [ "localhost:9113" ];
          }];
        }
        {
          job_name = "postgres";
          static_configs = [{
            targets = [ "localhost:9187" ];
          }];
        }
        {
          job_name = "redis";
          static_configs = [{
            targets = [ "localhost:9121" ];
          }];
        }
      ];
    };

    grafana = {
      enable = true;
      domain = "dashboard.example.com";
      port = 3000;
      addr = "127.0.0.1";
      auth.anonymous.enable = false;
      provision = {
        enable = true;
        datasources = {
          settings = {
            apiVersion = 1;
            datasources = [
              {
                name = "Prometheus";
                type = "prometheus";
                url = "http://localhost:9090";
                access = "proxy";
                isDefault = true;
              }
            ];
          };
        };
      };
    };

    # Email server (Postfix)
    postfix = {
      enable = true;
      hostname = "mail.example.com";
      domain = "example.com";
      origin = "example.com";
      rootAlias = "admin";
      sslCert = "/var/lib/acme/example.com/fullchain.pem";
      sslKey = "/var/lib/acme/example.com/key.pem";
      enableSubmission = true;
      enableSubmissions = true;
      submissionOptions = {
        smtpd_tls_security_level = "encrypt";
        smtpd_sasl_auth_enable = "yes";
        smtpd_client_restrictions = "permit_sasl_authenticated,reject";
      };
    };

    # ACME certificates
    acme = {
      acceptTerms = true;
      email = "admin@example.com";
      certs = {
        "example.com" = {
          extraDomainNames = [ "www.example.com" "dashboard.example.com" "mail.example.com" ];
          dnsProvider = "cloudflare";
          credentialsFile = "/var/lib/secrets/cloudflare.secret";
        };
      };
    };

    # System logging with Journald
    journald.extraConfig = ''
      SystemMaxUse=2G
      MaxRetentionSec=1month
      ForwardToSyslog=yes
    '';

    # Automatic updates
    auto-upgrade = {
      enable = true;
      allowReboot = true;
      dates = "04:00";
      rebootWindow = {
        lower = "04:00";
        upper = "06:00";
      };
    };

    # Fail2ban for intrusion prevention
    fail2ban = {
      enable = true;
      jails = {
        sshd = ''
          enabled = true
          maxretry = 5
          findtime = 600
          bantime = 3600
        '';
        nginx-http-auth = ''
          enabled = true
          port = http,https
          filter = nginx-http-auth
          logpath = /var/log/nginx/error.log
          maxretry = 5
          findtime = 600
          bantime = 3600
        '';
      };
    };

    # Backups with Restic
    restic.backups = {
      localbackup = {
        paths = [ "/home" "/var/lib/postgresql" "/etc" ];
        repository = "/mnt/backup-disk/restic-repo";
        initialize = true;
        passwordFile = "/var/lib/secrets/restic-password";
        timerConfig = {
          OnCalendar = "daily";
          Persistent = true;
        };
        pruneOpts = [
          "--keep-daily 7"
          "--keep-weekly 4"
          "--keep-monthly 3"
        ];
      };
    };
  };

  # Enable Docker
  virtualisation = {
    docker = {
      enable = true;
      autoPrune.enable = true;
      extraOptions = "--storage-driver overlay2";
    };
  };

  # User accounts
  users.users = {
    admin = {
      isNormalUser = true;
      description = "Administrator";
      extraGroups = [ "wheel" "networkmanager" "docker" "admins" ];
      openssh.authorizedKeys.keys = [
        "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQC2xh0SnVxmv/cPN7aOzxT0N1xB0CnGJ3IBsue8ICHoqW4besRGG6Kx3yFYyPEFJh5PYYmYcMEoC9MUNnNn+32FQYdAELv80QS4MNj1Nzsa/GNfm5g53n/ggZr/xkuBEeWGYl/B8cQPJH0z4UfxjtxCG/c1B5slJJy0Vv6O3JEGAWk3cuGCHlNZM7yJdPnxRcL5dGamZ7P9OY3DCBFvg9QxZJRpQXC43BA1Tl1UwCS/6zacwFsW+PLvfwN/mPK/tnRCKODVGiwWvDzVcnIZr9QJUHcOeg8QEX0AzB72up7MJQJoUV5hikXcYcQ9WDQYdrSWIT9N34z2uEtWrXvdhJWmW5I3ERrm0fZOcC7fZwbZ/LpCmqYL2BPaFRw9NIqJ3Yza7WXZ5AC2A0PgCPyITn+4FIn6Fd/UbSpO6p4NkgbuVniiQXQHxWHMkrElXFEpz9xHNE5bqbFEOQvn0qYwA/uZ4MdRy1bHJ4r1RBznjd2QCgdizpn5QiTMRt2Qve0mDWj1y0brIVnoYnWiF8T7X9n0C3JZxFjkHRfC5KzLU74EsPMbY1iCJ2BWJB8OW6JJYdagCLCvjVhwcfMXbXBD1Zptz21z67CtT+xOVNeJUbXsXHvtLqcKSZKSu3JOPvXb3eUBnRdqHO8NyVz5yBdW1HCiKWVaYbRQi61n8XPg1iZ8hQ== admin@example.com"
      ];
      hashedPassword = "$6$rounds=65536$salt$hash";
    };
    app = {
      isNormalUser = true;
      description = "Application User";
      extraGroups = [ "nginx" ];
      hashedPassword = "$6$rounds=65536$salt$hash";
    };
    backup = {
      isSystemUser = true;
      description = "Backup User";
      group = "backup";
      home = "/var/backup";
      createHome = true;
    };
  };

  # User groups
  users.groups = {
    admins = { };
    backup = { };
  };

  # Security settings
  security = {
    sudo.extraRules = [
      {
        groups = [ "wheel" ];
        commands = [ "ALL" ];
      }
      {
        groups = [ "admins" ];
        commands = [
          {
            command = "${pkgs.systemd}/bin/systemctl restart nginx";
            options = [ "NOPASSWD" ];
          }
          {
            command = "${pkgs.systemd}/bin/systemctl restart postgresql";
            options = [ "NOPASSWD" ];
          }
        ];
      }
    ];
    acme = {
      acceptTerms = true;
      email = "admin@example.com";
    };
    audit = {
      enable = true;
      rules = [
        "-a exit,always -F arch=b64 -F euid=0 -S execve"
        "-a exit,always -F arch=b32 -F euid=0 -S execve"
      ];
    };
    pam.loginLimits = [
      {
        domain = "*";
        type = "soft";
        item = "nofile";
        value = "4096";
      }
      {
        domain = "*";
        type = "hard";
        item = "nofile";
        value = "10240";
      }
    ];
  };

  # System packages
  environment.systemPackages = with pkgs; [
    # System utilities
    coreutils
    curl
    wget
    vim
    nano
    git
    htop
    tmux
    tree
    ripgrep
    fd
    jq
    unzip
    lsof
    ncdu
    iotop
    nmap
    tcpdump
    nload
    iftop

    # Security tools
    gnupg
    openssl
    fail2ban
    wireguard-tools
    ufw

    # Monitoring and backup
    prometheus
    grafana
    restic
    borgbackup

    # Containers and virtualization
    docker-compose
    podman
    kubectl
    k9s

    # Development tools
    gcc
    gnumake
    nodejs
    python3
    python3Packages.pip
    python3Packages.virtualenv
    go
    rustc
    cargo
  ];

  # Program configurations
  programs = {
    bash = {
      enableCompletion = true;
      shellAliases = {
        ll = "ls -la";
        update = "sudo nixos-rebuild switch";
        upgrade = "sudo nixos-rebuild switch --upgrade";
      };
      interactiveShellInit = ''
        export HISTCONTROL=ignoreboth
        export HISTSIZE=10000
        export HISTFILESIZE=20000
        shopt -s histappend
        export PATH=$HOME/bin:$PATH
      '';
    };

    vim = {
      defaultEditor = true;
      package = pkgs.vim-full;
    };

    tmux = {
      enable = true;
      shortcut = "a";
      terminal = "screen-256color";
      extraConfig = ''
        set -g mouse on
        set -g history-limit 10000
      '';
    };

    git = {
      enable = true;
      config = {
        init = {
          defaultBranch = "main";
        };
        user = {
          name = "Server Admin";
          email = "admin@example.com";
        };
      };
    };

    ssh = {
      startAgent = true;
      extraConfig = ''
        Host *
          ServerAliveInterval 60
          ServerAliveCountMax 30
      '';
    };

    zsh = {
      enable = true;
      enableCompletion = true;
      autosuggestions.enable = true;
      syntaxHighlighting.enable = true;
      ohMyZsh = {
        enable = true;
        theme = "robbyrussell";
        plugins = [ "git" "docker" "sudo" "copyfile" ];
      };
    };
  };

  # Filesystem configuration
  fileSystems = {
    "/" = {
      device = "/dev/disk/by-label/nixos";
      fsType = "ext4";
      options = [ "defaults" "noatime" ];
    };
    "/boot" = {
      device = "/dev/disk/by-label/boot";
      fsType = "vfat";
    };
    "/data" = {
      device = "/dev/disk/by-label/data";
      fsType = "ext4";
      options = [ "defaults" "noatime" ];
    };
    "/backup" = {
      device = "/dev/disk/by-uuid/12345678-1234-1234-1234-123456789abc";
      fsType = "ext4";
      options = [ "defaults" "noatime" ];
    };
  };

  # Swap configuration
  swapDevices = [
    {
      device = "/dev/disk/by-label/swap";
    }
  ];

  # Nix package management configuration
  nix = {
    settings = {
      auto-optimise-store = true;
      experimental-features = [ "nix-command" "flakes" ];
      trusted-users = [ "root" "admin" ];
      substituters = [
        "https://cache.nixos.org"
        "https://nix-community.cachix.org"
      ];
      trusted-public-keys = [
        "cache.nixos.org-1:6NCHdD59X431o0gWypbMrAURkbJ16ZPMQFGspcDShjY="
        "nix-community.cachix.org-1:mB9FSh9qf2dCimDSUo8Zy7bkq5CX+/rkCWyvRCYg3Fs="
      ];
    };
    gc = {
      automatic = true;
      dates = "weekly";
      options = "--delete-older-than 30d";
    };
    package = pkgs.nixVersions.stable;
    # Removed reference to inputs.nixpkgs as it's not available in this context
  };

  # System state version
  system.stateVersion = "23.11"; # Compatible with NixOS 23.11 release


  # Home Manager integration
  # This assumes you have home-manager as a module
  home-manager = {
    useGlobalPkgs = true;
    useUserPackages = true;
    users.admin = import ./home-manager/admin.nix;
    users.app = import ./home-manager/app.nix;
  };


}
