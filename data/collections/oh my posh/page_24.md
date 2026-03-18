Source URL: https://ohmyposh.dev/docs/contributing/segment

[Skip to main content](https://ohmyposh.dev/docs/contributing/segment#__docusaurus_skipToContent_fallback)

If you're enjoying Oh My Posh, consider becoming a [sponsor](https://github.com/sponsors/JanDeDobbeleer)
 to keep the project going strong 💪

On this page

Adding a new segment to Oh My Posh involves several steps to ensure proper integration. This guide walks you through creating a complete segment with all necessary files and registrations.

Planning Your Segment[​](https://ohmyposh.dev/docs/contributing/segment#planning-your-segment "Direct link to Planning Your Segment")

--------------------------------------------------------------------------------------------------------------------------------------

Before coding, define these key properties:

*   **Segment ID**: A kebab-case identifier used in configs (e.g., `new-feature`)
*   **Go Type Name**: PascalCase struct name for the code (e.g., `NewFeature`)
*   **Category**: Choose from `cli`, `cloud`, `health`, `languages`, `music`, `scm`, `system`, or `web`
*   **Description**: A clear one-line explanation of what the segment does
*   **Properties**: List of configurable properties with types and defaults
*   **Template**: Default template string (e.g., `{{ .Text }}`)

Automated Setup (VS Code)[​](https://ohmyposh.dev/docs/contributing/segment#automated-setup-vs-code "Direct link to Automated Setup (VS Code)")

------------------------------------------------------------------------------------------------------------------------------------------------

If you're using VS Code, you can use the automated segment creation command in VS Code Chat:

1.  Open VS Code Chat (use the Chat icon in the sidebar or Command Palette: "Chat: Focus on Chat View")
2.  Type `/segment` and follow the prompts
3.  Provide your segment details when requested
4.  The command will automatically create all necessary files and registrations

This automated approach ensures all files are created correctly with proper naming conventions and alphabetical ordering. If you prefer to create the segment manually or want to understand the process, continue with the manual steps below.

Manual Setup Steps[​](https://ohmyposh.dev/docs/contributing/segment#manual-setup-steps "Direct link to Manual Setup Steps")

-----------------------------------------------------------------------------------------------------------------------------

Step 1: Create the Go Implementation[​](https://ohmyposh.dev/docs/contributing/segment#step-1-create-the-go-implementation "Direct link to Step 1: Create the Go Implementation")

----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Create a new file in `./src/segments/` named after your segment ID: `new_feature.go`.

    package segmentsimport (	"github.com/jandedobbeleer/oh-my-posh/src/segments/options")type NewFeature struct {	Base	// Fields that will be available in your template	Text string}// Define constants for each configurable propertyconst (	// EnableNewThing enables the new functionality	EnableNewThing options.Property = "enable_new_thing"	// CustomText sets custom display text	CustomText options.Property = "custom_text")func (n *NewFeature) Enabled() bool {	// Set up data for the template using property values	n.Text = n.props.GetString(CustomText, "default value")	// Return true if the segment should be displayed	// You can add logic here to determine if the segment is relevant	return true}func (n *NewFeature) Template() string {	return "{{ .Text }}"}

**Key Guidelines:**

*   Use UTF32 representation for icons (e.g., `"\uEFF1"`) instead of the actual icons
*   Find icon codes at [Nerd Fonts Cheat Sheet](https://www.nerdfonts.com/cheat-sheet)
    
*   Keep the logic in `Enabled()` focused on data preparation and visibility determination

Step 2: Register Your Segment[​](https://ohmyposh.dev/docs/contributing/segment#step-2-register-your-segment "Direct link to Step 2: Register Your Segment")

-------------------------------------------------------------------------------------------------------------------------------------------------------------

Edit `src/config/segment_types.go` to register your new segment:

### Add Gob Registration[​](https://ohmyposh.dev/docs/contributing/segment#add-gob-registration "Direct link to Add Gob Registration")

In the `init()` function, add your segment to the gob registry (maintain alphabetical order):

    gob.Register(&segments.NewFeature{})

### Add Segment Constant[​](https://ohmyposh.dev/docs/contributing/segment#add-segment-constant "Direct link to Add Segment Constant")

Add a constant for your segment type (maintain alphabetical order):

    // NEWFEATURE displays new feature informationNEWFEATURE SegmentType = "new-feature"

### Add to Segments Map[​](https://ohmyposh.dev/docs/contributing/segment#add-to-segments-map "Direct link to Add to Segments Map")

Register your segment in the `Segments` map (maintain alphabetical order):

    NEWFEATURE: func() SegmentWriter { return &segments.NewFeature{} },

Step 3: Create Documentation[​](https://ohmyposh.dev/docs/contributing/segment#step-3-create-documentation "Direct link to Step 3: Create Documentation")

----------------------------------------------------------------------------------------------------------------------------------------------------------

Create documentation at `website/docs/segments/[category]/[segment-id].mdx`:

    ---id: new-featuretitle: New Featuresidebar_label: New Feature---## WhatDisplays information about the new feature in your environment.## Sample Configurationimport Config from "@site/src/components/Config.js";<Config  data={{    type: "new-feature",    style: "powerline",    powerline_symbol: "\uE0B0",    foreground: "#193549",    background: "#ffeb3b",    options: {      enable_new_thing: true,      custom_text: "Hello World",    },  }}/>## Options| Name               | Type      | Default | Description                   || ------------------ | --------- | ------- | ----------------------------- || `enable_new_thing` | `boolean` | `false` | Enables the new functionality || `custom_text`      | `string`  | `""`    | Custom text to display        |

Step 4: Update Sidebar Navigation[​](https://ohmyposh.dev/docs/contributing/segment#step-4-update-sidebar-navigation "Direct link to Step 4: Update Sidebar Navigation")

-------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Edit `website/sidebars.js` and add your documentation to the appropriate category (maintain alphabetical order):

    {  type: "category",  label: "🖥️ System", // or appropriate category  collapsed: true,  items: [    // ... other segments    "segments/system/new-feature",    // ... more segments  ]}

Step 5: Add JSON Schema Definition[​](https://ohmyposh.dev/docs/contributing/segment#step-5-add-json-schema-definition "Direct link to Step 5: Add JSON Schema Definition")

----------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Update `themes/schema.json` in two places:

### Add to Type Enum[​](https://ohmyposh.dev/docs/contributing/segment#add-to-type-enum "Direct link to Add to Type Enum")

In the segment type enum, add your segment ID (maintain alphabetical order):

    {  "enum": [    "angular",    // ... other types    "new-feature"    // ... more types  ]}

### Add Schema Definition[​](https://ohmyposh.dev/docs/contributing/segment#add-schema-definition "Direct link to Add Schema Definition")

In the `allOf` array, add your segment's property schema (maintain alphabetical order):

    {  "if": {    "properties": {      "type": { "const": "new-feature" }    }  },  "then": {    "title": "New Feature Segment",    "description": "https://ohmyposh.dev/docs/segments/system/new-feature",    "properties": {      "options": {        "properties": {          "enable_new_thing": {            "type": "boolean",            "title": "Enable New Thing",            "description": "Enables the new functionality",            "default": false          },          "custom_text": {            "type": "string",            "title": "Custom Text",            "description": "Custom text to display",            "default": ""          }        }      }    }  }}

Step 6: Add Tests[​](https://ohmyposh.dev/docs/contributing/segment#step-6-add-tests "Direct link to Step 6: Add Tests")

-------------------------------------------------------------------------------------------------------------------------

Create a test file `src/segments/new_feature_test.go` using table-driven tests:

    package segmentsimport (	"testing"	"github.com/jandedobbeleer/oh-my-posh/src/segments/options"	"github.com/jandedobbeleer/oh-my-posh/src/runtime/mock")func TestNewFeature(t *testing.T) {	cases := []struct {		Case     string		Template string		CustomText string		Expected string	}{		{Case: "default", CustomText: "", Expected: ""},		{Case: "custom text", CustomText: "Hello", Expected: "Hello"},	}	for _, tc := range cases {		t.Run(tc.Case, func(t *testing.T) {			env := &mock.Environment{}			props := options.Map{				CustomText: tc.CustomText,			}			segment := &NewFeature{}			segment.Init(props, env)			if !segment.Enabled() {				t.Error("Expected segment to be enabled")			}			if segment.Text != tc.Expected {				t.Errorf("Expected %s, got %s", tc.Expected, segment.Text)			}		})	}}

Look at [existing segment tests](https://github.com/JanDeDobbeleer/oh-my-posh/blob/main/src/segments/az_test.go)
 for more complex examples and inspiration.

Step 7: Build and Test[​](https://ohmyposh.dev/docs/contributing/segment#step-7-build-and-test "Direct link to Step 7: Build and Test")

----------------------------------------------------------------------------------------------------------------------------------------

Validate your implementation by building the project:

    go build -v

Run your specific tests:

    go test ./src/segments/new_feature_test.go

Important Guidelines[​](https://ohmyposh.dev/docs/contributing/segment#important-guidelines "Direct link to Important Guidelines")

-----------------------------------------------------------------------------------------------------------------------------------

### File Organization[​](https://ohmyposh.dev/docs/contributing/segment#file-organization "Direct link to File Organization")

*   **Segment files**: `src/segments/[segment_id].go`
*   **Test files**: `src/segments/[segment_id]_test.go`
*   **Documentation**: `website/docs/segments/[category]/[segment-id].mdx`\### Alphabetical Ordering Maintain alphabetical order in:
*   `init()` gob registrations in `segment_types.go`
*   Segment type constants in `segment_types.go`
*   Segments map entries in `segment_types.go`
*   Schema type enum in `themes/schema.json`
*   Schema `allOf` definitions in `themes/schema.json`
*   Sidebar navigation items in `sidebars.js`

### Code Quality[​](https://ohmyposh.dev/docs/contributing/segment#code-quality "Direct link to Code Quality")

*   Use meaningful property names and constants
*   Include descriptive comments for options
*   Keep `Enabled()` logic focused and efficient
*   Use UTF32 codes for icons, not the actual icons
*   Follow Go naming conventions (PascalCase for exported items)

### Documentation Standards[​](https://ohmyposh.dev/docs/contributing/segment#documentation-standards "Direct link to Documentation Standards")

*   Use `.mdx` extension for documentation files
*   Include complete property tables with types, descriptions, and defaults
*   Provide realistic sample configurations
*   Keep line lengths under 120 characters
*   Use proper headings and formatting

Resources[​](https://ohmyposh.dev/docs/contributing/segment#resources "Direct link to Resources")

--------------------------------------------------------------------------------------------------

*   [Nerd Fonts Cheat Sheet](https://www.nerdfonts.com/cheat-sheet)
     - Find icon UTF32 codes
*   [Existing Tests](https://github.com/JanDeDobbeleer/oh-my-posh/blob/main/src/segments/az_test.go)
     - Examples for test patterns
*   [Table-Driven Tests](https://blog.alexellis.io/golang-writing-unit-tests/)
     - Go testing best practices

Create a Pull Request[​](https://ohmyposh.dev/docs/contributing/segment#create-a-pull-request "Direct link to Create a Pull Request")

--------------------------------------------------------------------------------------------------------------------------------------

Once you've completed all steps:

1.  **Verify everything builds**: `go build -v`
2.  **Run tests**: `go test ./src/segments/[your_segment]_test.go`
3.  **Check formatting**: Ensure your code follows Go formatting standards
4.  **Review checklist**: All files created/updated as described above
5.  **Create PR**: Include a clear description of what your segment does

Be patient during the review process! 🏎

*   [Planning Your Segment](https://ohmyposh.dev/docs/contributing/segment#planning-your-segment)
    
*   [Automated Setup (VS Code)](https://ohmyposh.dev/docs/contributing/segment#automated-setup-vs-code)
    
*   [Manual Setup Steps](https://ohmyposh.dev/docs/contributing/segment#manual-setup-steps)
    
*   [Step 1: Create the Go Implementation](https://ohmyposh.dev/docs/contributing/segment#step-1-create-the-go-implementation)
    
*   [Step 2: Register Your Segment](https://ohmyposh.dev/docs/contributing/segment#step-2-register-your-segment)
    *   [Add Gob Registration](https://ohmyposh.dev/docs/contributing/segment#add-gob-registration)
        
    *   [Add Segment Constant](https://ohmyposh.dev/docs/contributing/segment#add-segment-constant)
        
    *   [Add to Segments Map](https://ohmyposh.dev/docs/contributing/segment#add-to-segments-map)
        
*   [Step 3: Create Documentation](https://ohmyposh.dev/docs/contributing/segment#step-3-create-documentation)
    
*   [Step 4: Update Sidebar Navigation](https://ohmyposh.dev/docs/contributing/segment#step-4-update-sidebar-navigation)
    
*   [Step 5: Add JSON Schema Definition](https://ohmyposh.dev/docs/contributing/segment#step-5-add-json-schema-definition)
    *   [Add to Type Enum](https://ohmyposh.dev/docs/contributing/segment#add-to-type-enum)
        
    *   [Add Schema Definition](https://ohmyposh.dev/docs/contributing/segment#add-schema-definition)
        
*   [Step 6: Add Tests](https://ohmyposh.dev/docs/contributing/segment#step-6-add-tests)
    
*   [Step 7: Build and Test](https://ohmyposh.dev/docs/contributing/segment#step-7-build-and-test)
    
*   [Important Guidelines](https://ohmyposh.dev/docs/contributing/segment#important-guidelines)
    *   [File Organization](https://ohmyposh.dev/docs/contributing/segment#file-organization)
        
    *   [Code Quality](https://ohmyposh.dev/docs/contributing/segment#code-quality)
        
    *   [Documentation Standards](https://ohmyposh.dev/docs/contributing/segment#documentation-standards)
        
*   [Resources](https://ohmyposh.dev/docs/contributing/segment#resources)
    
*   [Create a Pull Request](https://ohmyposh.dev/docs/contributing/segment#create-a-pull-request)