Source URL: https://ohmyposh.dev/docs/segments/health/ramadan

[Skip to main content](https://ohmyposh.dev/docs/segments/health/ramadan#__docusaurus_skipToContent_fallback)

If you're enjoying Oh My Posh, consider becoming a [sponsor](https://github.com/sponsors/JanDeDobbeleer)
 to keep the project going strong 💪

On this page

What[​](https://ohmyposh.dev/docs/segments/health/ramadan#what "Direct link to What")

--------------------------------------------------------------------------------------

Displays Sehar (Fajr) and Iftar (Maghrib) prayer times along with a countdown to the next event during Ramadan. Powered by the free [Aladhan Prayer Times API](https://aladhan.com/prayer-times-api)
. The segment auto-hides when it is not Ramadan (configurable via `hide_outside_ramadan`).

Sample Configuration[​](https://ohmyposh.dev/docs/segments/health/ramadan#sample-configuration "Direct link to Sample Configuration")

--------------------------------------------------------------------------------------------------------------------------------------

*   json
*   yaml
*   toml

    {  "type": "ramadan",  "style": "diamond",  "foreground": "#ffffff",  "background": "#1a472a",  "leading_diamond": "",  "trailing_diamond": "",  "template": "U0001F319 Roza {{.RozaNumber}} · {{.NextEvent}} in {{.TimeRemaining}}",  "options": {    "city": "Lahore",    "country": "PK",    "method": 1,    "school": 1  }}

    type: ramadanstyle: diamondforeground: "#ffffff"background: "#1a472a"leading_diamond: trailing_diamond: template: U0001F319 Roza {{.RozaNumber}} · {{.NextEvent}} in {{.TimeRemaining}}options:  city: Lahore  country: PK  method: 1  school: 1

    type = "ramadan"style = "diamond"foreground = "#ffffff"background = "#1a472a"leading_diamond = ""trailing_diamond = ""template = "U0001F319 Roza {{.RozaNumber}} · {{.NextEvent}} in {{.TimeRemaining}}"[options]city = "Lahore"country = "PK"method = 1school = 1

Options[​](https://ohmyposh.dev/docs/segments/health/ramadan#options "Direct link to Options")

-----------------------------------------------------------------------------------------------

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `latitude` | `float64` | `0` | Latitude for prayer time calculation (use with `longitude`) |
| `longitude` | `float64` | `0` | Longitude for prayer time calculation (use with `latitude`) |
| `city` | `string` | `""` | City name for location lookup — takes precedence over `latitude`/`longitude` |
| `country` | `string` | `""` | Country name or ISO 3166 alpha-2 code — required when using `city` |
| `method` | `int` | `3` | Prayer calculation method (0–23, 99). See [Aladhan methods](https://aladhan.com/calculation-methods)<br> for details |
| `school` | `int` | `0` | Madhab school: `0` = Shafi (standard), `1` = Hanafi |
| `hide_outside_ramadan` | `bool` | `true` | Hide the segment when not in Ramadan |
| `first_roza_date` | `string` | `""` | Override first day of Ramadan as `YYYY-MM-DD` for local moon sighting |
| `http_timeout` | `int` | `20` | HTTP request timeout in milliseconds |

info

Either **city + country** or **latitude + longitude** must be configured. If both are provided, `city` + `country` takes precedence.

Prayer calculation methods

Use the method associated with the issuing authority closest to your location. The full ID→authority mapping is:

| ID  | Authority |
| --- | --- |
| 0   | Shia Ithna-Ashari, Leva Institute, Qum |
| 1   | University of Islamic Sciences, Karachi |
| 2   | Islamic Society of North America (ISNA) |
| 3   | Muslim World League (**default**) |
| 4   | Umm Al-Qura University, Makkah |
| 5   | Egyptian General Authority of Survey |
| 7   | Institute of Geophysics, University of Tehran |
| 8   | Gulf Region |
| 9   | Kuwait |
| 10  | Qatar |
| 11  | Majlis Ugama Islam Singapura, Singapore |
| 12  | Union Organisation Islamique de France |
| 13  | Diyanet İşleri Başkanlığı, Turkey _(experimental)_ |
| 14  | Spiritual Administration of Muslims of Russia |
| 15  | Moonsighting Committee Worldwide |
| 16  | Dubai _(experimental)_ |
| 17  | Jabatan Kemajuan Islam Malaysia (JAKIM) |
| 18  | Tunisia |
| 19  | Algeria |
| 20  | Kementerian Agama Republik Indonesia |
| 21  | Morocco |
| 22  | Comunidade Islâmica de Lisboa, Portugal |
| 23  | Ministry of Awqaf, Islamic Affairs and Holy Places, Jordan |
| 99  | Custom (use `methodSettings` via the API) |

Note: ID 6 is not assigned.

Template ([info](https://ohmyposh.dev/docs/configuration/templates)
)[​](https://ohmyposh.dev/docs/segments/health/ramadan#template-info "Direct link to template-info")

-------------------------------------------------------------------------------------------------------------------------------------------------------------------------

default template

     🌙 Roza {{.RozaNumber}} · {{.NextEvent}} in {{.TimeRemaining}}

### Properties[​](https://ohmyposh.dev/docs/segments/health/ramadan#properties "Direct link to Properties")

| Name | Type | Description |
| --- | --- | --- |
| `.Fajr` | `string` | Sehar (Fajr) time in `HH:MM` format |
| `.Iftar` | `string` | Iftar (Maghrib) time in `HH:MM` format |
| `.Imsak` | `string` | Imsak time in `HH:MM` format (~10 min before Fajr) |
| `.RozaNumber` | `int` | Day number within Ramadan (1–30) |
| `.NextEvent` | `string` | Name of the next event: `Sehar` or `Iftar` |
| `.TimeRemaining` | `string` | Countdown to the next event, e.g. `3h 42m` |
| `.Fasting` | `bool` | `true` when currently between Fajr and Maghrib (fasting window) |

*   [What](https://ohmyposh.dev/docs/segments/health/ramadan#what)
    
*   [Sample Configuration](https://ohmyposh.dev/docs/segments/health/ramadan#sample-configuration)
    
*   [Options](https://ohmyposh.dev/docs/segments/health/ramadan#options)
    
*   [Template (info)](https://ohmyposh.dev/docs/segments/health/ramadan#template-info)
    *   [Properties](https://ohmyposh.dev/docs/segments/health/ramadan#properties)