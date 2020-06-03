# plugin-reports

development configuration:


```json
{
  "app_title": "Reports",
  "languages": ["en"],
  "plugins": [
    {
      "name": "rogerthat_api",
      "order": 0,
      "version": "master",
      "url": "https://github.com/our-city-app/plugin-mobicage-api.git",
      "configuration":{
        "rogerthat_server_url": "https://rogerthat-server.appspot.com"
      },
      "configuration_development":{
        "rogerthat_server_url": "http://localhost:8080"
      }
    },
    {
      "name": "interactive_explorer",
      "order": 42,
      "version": "master",
      "url": "https://github.com/our-city-app/plugin-interactive-explorer.git"
    },
    {
      "name": "basic_auth",
      "order": -1,
      "version": "master",
      "url": "https://github.com/our-city-app/plugin-basic-auth.git",
      "configuration": {
        "cookie_key": "some cookie key",
        "allowed_google_domains": ["mobicage.com"]
      }
    },
    {
      "name": "reports",
      "order": 1,
      "version": "master",
      "url": "https://github.com/our-city-app/plugin-reports.git",
      "configuration": {
        "google_maps_key": "gmaps key",
        "oca_server_secret": "reports-dev-secret",
        "gv_proxies": [
          {
            "id": "dev",
            "url": "http://localhost:5000",
            "secret": "DEV PROXY SECRET"
          }
        ]
      },
      "client_configuration": {
        "gv_proxies": [
          {"id": "dev"},
        ]
      }
      }
    }
  ]
}

```