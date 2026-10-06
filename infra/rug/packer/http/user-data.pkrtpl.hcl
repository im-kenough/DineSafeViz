#cloud-config
autoinstall:
  version: 1
  locale: en_US.UTF-8
  keyboard:
    layout: us
  identity:
    hostname: ubuntu-server
    password: "$6$ex.yPzz0$wIghQ4Gj4h4tM/5bF8aHMyk4Z2HnK/9a7d3R8O9zV5fXz7g.H7z3Q8K2k9y.1X3b6c2R7x/W8Q3d2k0g7L9A2."
    realname: adm-ubuntu
    username: adm-ubuntu
  ssh:
    install-server: true
    allow-pw: true
  storage:
    layout:
      name: direct
  user-data:
    package_upgrade: true
    packages:
      - qemu-guest-agent
      - cloud-init
    users:
      - name: adm-ubuntu
        ssh_authorized_keys:
          - ${ssh_key}
