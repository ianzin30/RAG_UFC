[Skip to main content](https://ohmyposh.dev/docs/segments/languages/rust#__docusaurus_skipToContent_fallback)

If you're enjoying Oh My Posh, consider becoming a [sponsor](https://github.com/sponsors/JanDeDobbeleer) to keep the project going strong 💪

On this page

## What [​](https://ohmyposh.dev/docs/segments/languages/rust\#what "Direct link to What")

Display the currently active [Rust](https://rust-lang.org/) version.

## Sample Configuration [​](https://ohmyposh.dev/docs/segments/languages/rust\#sample-configuration "Direct link to Sample Configuration")

- json
- yaml
- toml

```json
{
  "type": "rust",
  "style": "powerline",
  "powerline_symbol": "",
  "foreground": "#193549",
  "background": "#99908a",
  "template": "  {{ .Full }} "
}
```

```yaml
type: rust
style: powerline
powerline_symbol: 
foreground: "#193549"
background: "#99908a"
template: "  {{ .Full }} "
```

```toml
type = "rust"
style = "powerline"
powerline_symbol = ""
foreground = "#193549"
background = "#99908a"
template = "  {{ .Full }} "
```

## Options [​](https://ohmyposh.dev/docs/segments/languages/rust\#options "Direct link to Options")

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `home_enabled` | `boolean` | `false` | display the segment in the HOME folder or not |
| `fetch_version` | `boolean` | `true` | fetch the rust version (`rustc --version`) |
| `cache_duration` | `string` | `none` | the duration for which the version will be cached. The duration is a string in the format `1h2m3s` and is parsed using the [time.ParseDuration](https://golang.org/pkg/time/#ParseDuration) function from the Go standard library. To disable the cache, use `none` |
| `missing_command_text` | `string` |  | text to display when the command is missing |
| `display_mode` | `string` | `context` | - `always`: the segment is always displayed<br>- `files`: the segment is only displayed when file `extensions` listed are present<br>- `context`: displays the segment when the environment or files is active |
| `version_url_template` | `string` |  | a go [text/template](https://golang.org/pkg/text/template/) [template](https://ohmyposh.dev/docs/configuration/templates) that creates the URL of the version info / release notes |
| `extensions` | `[]string` | `*.rs, Cargo.toml, Cargo.lock` | allows to override the default list of file extensions to validate |
| `folders` | `[]string` |  | allows to override the list of folder names to validate |
| `tooling` | `[]string` | `rustc` | the tooling to use for fetching the version |

## Template ( [info](https://ohmyposh.dev/docs/configuration/templates)) [​](https://ohmyposh.dev/docs/segments/languages/rust\#template-info "Direct link to template-info")

default template

```template
{{ if .Error }}{{ .Error }}{{ else }}{{ .Full }}{{ end }}
```

### Properties [​](https://ohmyposh.dev/docs/segments/languages/rust\#properties "Direct link to Properties")

| Name | Type | Description |
| --- | --- | --- |
| `.Full` | `string` | the full version |
| `.Major` | `string` | major number |
| `.Minor` | `string` | minor number |
| `.Patch` | `string` | patch number |
| `.Prerelease` | `string` | channel name |
| `.Error` | `string` | error encountered when fetching the version string |

- [What](https://ohmyposh.dev/docs/segments/languages/rust#what)
- [Sample Configuration](https://ohmyposh.dev/docs/segments/languages/rust#sample-configuration)
- [Options](https://ohmyposh.dev/docs/segments/languages/rust#options)
- [Template (info)](https://ohmyposh.dev/docs/segments/languages/rust#template-info)
  - [Properties](https://ohmyposh.dev/docs/segments/languages/rust#properties)