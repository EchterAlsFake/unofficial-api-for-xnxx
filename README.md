<h1 align="center">XNXX API</h1>
<p align="center"><em>An asynchronous Python API wrapper and scraper for xnxx.com</em></p>

<div align="center">
    <a href="https://pepy.tech/project/xnxx_api"><img src="https://static.pepy.tech/badge/xnxx_api" alt="Downloads"></a>
    <a href="https://github.com/EchterAlsFake/xnxx_api/workflows/"><img src="https://github.com/EchterAlsFake/xnxx_api/workflows/CodeQL/badge.svg" alt="CodeQL Analysis"/></a>
    <a href="https://echteralsfake.me/ci/xnxx_api/badge.svg"><img src="https://echteralsfake.me/ci/xnxx_api/badge.svg" alt="API Tests"/></a>
    </div>

# Disclaimer
> [!IMPORTANT]
> This is an unofficial and unaffiliated project. Please read the full disclaimer before use:
> **[DISCLAIMER.md](https://github.com/EchterAlsFake/API_Docs/blob/master/Disclaimer.md)**
>
> By using this project you agree to comply with the target site's rules, copyright/licensing requirements,
> and applicable laws. Do not use it to bypass access controls or scrape at disruptive rates.

---

# Features

| Category | Details |
|---|---|
| **Video Fetching** | Fetch video objects with full metadata (title, description, views, length, publish date, thumbnail) |
| **Video Downloading** | HLS-based downloading with configurable quality (`best`, `half`, `worst`, or specific resolutions) |
| **User Profiles** | Fetch user/model profiles including total video count, page count, and total video views |
| **Video Search** | Search with filters for quality (720p / 1080p+), length, upload time, and mode (hits / random) |
| **Async-First** | Fully asynchronous (`async` / `await`) built on top of `asyncio` |
| **Built-in Caching** | Automatic response caching with configurable limits to reduce redundant network requests |
| **CLI Support** | Command-line interface for quick downloads — run `xnxx_api -h` for options |
| **Type Safety** | Comprehensive type hinting and `dataclass`-based models throughout |

#### Networking Features

The networking layer is provided by the [`eaf_base_api`](https://github.com/EchterAlsFake/eaf_base_api) package and is fully configurable through `RuntimeConfig`:

| Feature | Description |
|---|---|
| **HTTP/1.1, HTTP/2, HTTP/3** | Configurable HTTP version (`v1`, `v2`, `v3` — defaults to HTTP/3) |
| **Browser Impersonation** | Built-in browser fingerprint impersonation via `curl_cffi` (defaults to Chrome) |
| **Custom JA3 Fingerprint** | Override the TLS fingerprint with a custom JA3 string for advanced use cases |
| **Proxy Support** | All proxy types supported (HTTP, HTTPS, SOCKS4, SOCKS5) |
| **Proxy Authentication** | Username/password authentication for proxies |
| **Bandwidth Limiting** | Set a maximum download speed in MB/s (e.g., `2.0`, `3.5`) |
| **DNS over HTTPS** | Route DNS queries over HTTPS for privacy and bypassing DNS-level blocks |
| **SSL Verification** | Toggle SSL certificate verification on or off |
| **Request Delay** | Configurable delay between requests to respect rate limits |
| **Concurrency Control** | Tune video and page concurrency independently for optimal throughput |

---

# Supported Platforms
This API has been tested and confirmed working on:

- Windows 11 (x64) 
- macOS Sequoia (x86_64)
- Linux (Arch) (x86_64)
- Android 16 (aarch64)

---

# Installation

> [!WARNING]
> The installation from Git is **temporary**. The package will be migrated to PyPI within the next week.

```bash
pip install git+https://github.com/EchterAlsFake/unofficial-api-for-beeg git+https://github.com/EchterAlsFake/eaf_base_api
```

---

# Quickstart

### Have a look at the [Documentation](https://docs.echteralsfake.me/xnxx) for more details


```python
import asyncio
from xnxx_api import Client, DownloadConfigHLS

async def main():
    # Initialize a Client object
    client = Client()
    
    # Fetch a video
    video_object = await client.get_video("<insert_url_here>")
    
    # Information from Video objects
    print(video_object.title)
    print(video_object.likes)
    # Download the video
    config = DownloadConfigHLS(quality="best", path="./") # More options in the documentation
    await video_object.download(config)

# SEE DOCUMENTATION FOR MORE
```

> [!NOTE]
> XNXX API can also be used from the command line. Do: xnxx_api -h to see the options

---

# Changelog
See [Changelog](https://github.com/EchterAlsFake/xnxx_api/blob/master/README/Changelog.md) for more details.

---

# Support the Project ❤️

I develop all my projects entirely for free because I enjoy it and want to keep them accessible.
If you find my work useful, please consider supporting me with a small donation — even 1 € makes a big difference and keeps me motivated!

### ☕ Ko-fi
<a href="https://ko-fi.com/EchterAlsFake">https://ko-fi.com/EchterAlsFake</a>

### 💳 PayPal
<a href="https://paypal.me/EchterAlsFake">https://paypal.me/EchterAlsFake</a>

### 🪙 Crypto (350+ currencies supported)
<a href="https://nowpayments.io/donation?api_key=65b1acaf-735d-4d4b-b3d6-c2237c0b57e3" target="_blank" rel="noreferrer noopener">
   <img src="https://nowpayments.io/images/embeds/donation-button-black.svg" alt="Crypto donation button by NOWPayments">
</a>

---

# Contribution
Do you see any issues or having some feature requests? Simply open an Issue or talk
in the discussions.

Pull requests are also welcome.

# License
Licensed under the LGPLv3 License
<br>Copyright (C) 2023–2026 Johannes Habel
