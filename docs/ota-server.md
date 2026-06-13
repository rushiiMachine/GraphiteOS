# OTA Server

## Self-Signed Certificates

If you do not have access to a domain (or wish to not depend on one) to generate
TLS certificates between the OTA server and Custota, you may use a self-signed certificate.
This will require generating a root CA certificate and adding it to the immutable system
trust store inside an OTA. Afterward, you can use a reverse proxy such as Caddy to serve
OTA files with a key signed by the root certificate.

> [!IMPORTANT]
> This does not support Android 14+ at the moment.

> [!WARNING]
> Adding a certificate to the system trust store will allow for MITM'ing any traffic from
> apps that do not perform SSL pinning! As such, you must take great care in keeping this
> root private key safe!

To start, install `openssl` on your system.

Generate your custom Root CA private key & certificate:

```shell
$ openssl req \
  -x509 \
  -newkey rsa:4096 \
  -sha256 \
  -days 3650 \
  -nodes \
  -keyout rootCA.key \
  -out rootCA.crt \
  -subj "/CN=My Root CA" \
  -addext "basicConstraints=critical,CA:TRUE" \
  -addext "keyUsage=critical,keyCertSign,cRLSignexit" \
  -addext "subjectKeyIdentifier=hash"
```

This produces a private key `rootCA.key` and certificate `rootCA.crt` in the current directory.

Next, generate a new, separate, private key to be used by the reverse proxy for TLS.

```shell
$ openssl genrsa -out server.key 2048
```

Next, generate a certificate signing request for any domain you wish to host your OTA server at.
Using a `.local` TLD for your domain will reduce the complexity, as resolving it will automatically
work on the local network through mDNS. Otherwise, you will have to set up a DNS server to resolve
that domain to your OTA server's IP on your phone (or make a `/etc/hosts` override).

```shell
$ openssl req \
  -new \
  -key server.key \
  -out server.csr \
  -subj "/CN=graphite.local" \
  -addext "keyUsage=critical,digitalSignature" \                                                                                                                                    
  -addext "extendedKeyUsage=serverAuth" \                                                                                                                                           
  -addext "basicConstraints=critical,CA:FALSE" \                                                                                                                                    
  -addext "subjectAltName=DNS:graphite.local"
```

Next, sign the CSR with your root CA certificate and key:

```shell
$ openssl x509 \
  -req \
  -in server.csr \
  -CA rootCA.crt \
  -CAkey rootCA.key \
  -CAcreateserial \
  -out server.crt \
  -days 365 \
  -sha256 \
  -copy_extensions copy
```

Note that this certificate expires after 1 year, but you may change the expiry to whatever desired.

Now, you may use the domain private key and certificate in your reverse proxy!
For example, this is a sample configuration for [Caddy](https://github.com/caddyserver/caddy):

```caddyfile
graphite.local {
    tls server.crt server.key
    
    root * /builds
    file_server
}
```

You can now quickly test whether your proxy works by curl'ing it:

```shell
$ curl -v https://graphite.local --resolve graphite.local:443:127.0.0.1 --cacert rootCA.crt
```

curl should return no errors.

You will also have to add your root CA certificate to the OTA.
There is a module already provided for you to do this:

```shell
uv run graphite.py patch \
  ... \
  --module-system-certs .keys/rootCA.crt
```
