# Network architecture

## DNS

- **Domain:** dinesafeviz.com
- **Registrar:** Namecheap
- **DNS provider:** Cloudflare

A Cloudflare redirect rule redirects `dinesafeviz.com` and
`www.dinesafeviz.com` to `https://github.com/im-kenough/DineSafeViz`.
Cloudflare handles the HTTP-to-HTTPS redirect automatically.

The following output shows the current DNS records.

```text
dinesafeviz.com.        282     IN      A       172.64.80.1
dinesafeviz.com.        282     IN      AAAA    2606:4700:130:436c:6f75:6466:6c61:7265
Trying "dinesafeviz.com"
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 62972
;; flags: qr rd ra; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 0

;; QUESTION SECTION:
;dinesafeviz.com.               IN      A

;; ANSWER SECTION:
dinesafeviz.com.        281     IN      A       172.64.80.1

Received 49 bytes from 127.0.0.53#53 in 1 ms
Trying "dinesafeviz.com"
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 4493
;; flags: qr rd ra; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 0

;; QUESTION SECTION:
;dinesafeviz.com.               IN      AAAA

;; ANSWER SECTION:
dinesafeviz.com.        281     IN      AAAA    2606:4700:130:436c:6f75:6466:6c61:7265

Received 61 bytes from 127.0.0.53#53 in 1 ms
Trying "dinesafeviz.com"
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 12087
;; flags: qr rd ra; QUERY: 1, ANSWER: 0, AUTHORITY: 1, ADDITIONAL: 0

;; QUESTION SECTION:
;dinesafeviz.com.               IN      MX

;; AUTHORITY SECTION:
dinesafeviz.com.        1800    IN      SOA     anna.ns.cloudflare.com. dns.cloudflare.com. 2408771467 10000 2400 604800 1800

Received 92 bytes from 127.0.0.53#53 in 270 ms
Trying "www.dinesafeviz.com"
Host www.dinesafeviz.com not found: 3(NXDOMAIN)
Received 37 bytes from 127.0.0.53#53 in 272 ms
Received 37 bytes from 127.0.0.53#53 in 272 ms
```

## IP address management (IPAM)

### Application

TODO: include a network diagram of the VM and the Docker Compose stack.

- App VM

### Infrastructure

TODO: add a network diagram that shows the IP information for the Proxmox host,
the image layers, and the app VM.

The Proxmox host is x.x.x.x.
