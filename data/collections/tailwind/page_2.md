You're looking at the documentation forTailwind CSS v2.

[Go to Tailwind CSS v3 →](https://tailwindcss.com/)

[Go to Tailwind CSS v3 →](https://tailwindcss.com/)

[Tailwind CSS home page](https://v2.tailwindcss.com/)

Quick search for anythingPress `Ctrl ` and `K` to search

Tailwind CSS Versionv3v2.2.16v1.9.6v0.7.4 [Tailwind CSS on GitHub](https://github.com/tailwindlabs/tailwindcss)

Open site navigation

# Customizing Colors

Customizing the default color palette for your project.

## Overview

Tailwind includes an expertly-crafted default color palette out-of-the-box that is a great starting point if you don’t have your own specific branding in mind.

Gray

`colors.coolGray`

50

#F9FAFB

100

#F3F4F6

200

#E5E7EB

300

#D1D5DB

400

#9CA3AF

500

#6B7280

600

#4B5563

700

#374151

800

#1F2937

900

#111827

Red

`colors.red`

50

#FEF2F2

100

#FEE2E2

200

#FECACA

300

#FCA5A5

400

#F87171

500

#EF4444

600

#DC2626

700

#B91C1C

800

#991B1B

900

#7F1D1D

Yellow

`colors.amber`

50

#FFFBEB

100

#FEF3C7

200

#FDE68A

300

#FCD34D

400

#FBBF24

500

#F59E0B

600

#D97706

700

#B45309

800

#92400E

900

#78350F

Green

`colors.emerald`

50

#ECFDF5

100

#D1FAE5

200

#A7F3D0

300

#6EE7B7

400

#34D399

500

#10B981

600

#059669

700

#047857

800

#065F46

900

#064E3B

Blue

`colors.blue`

50

#EFF6FF

100

#DBEAFE

200

#BFDBFE

300

#93C5FD

400

#60A5FA

500

#3B82F6

600

#2563EB

700

#1D4ED8

800

#1E40AF

900

#1E3A8A

Indigo

`colors.indigo`

50

#EEF2FF

100

#E0E7FF

200

#C7D2FE

300

#A5B4FC

400

#818CF8

500

#6366F1

600

#4F46E5

700

#4338CA

800

#3730A3

900

#312E81

Purple

`colors.violet`

50

#F5F3FF

100

#EDE9FE

200

#DDD6FE

300

#C4B5FD

400

#A78BFA

500

#8B5CF6

600

#7C3AED

700

#6D28D9

800

#5B21B6

900

#4C1D95

Pink

`colors.pink`

50

#FDF2F8

100

#FCE7F3

200

#FBCFE8

300

#F9A8D4

400

#F472B6

500

#EC4899

600

#DB2777

700

#BE185D

800

#9D174D

900

#831843

But when you do need to customize your palette, you can configure your colors under the `colors` key in the `theme` section of your `tailwind.config.js` file:

```js
// tailwind.config.js
module.exports = {
  theme: {
    colors: {
      // Configure your color palette here
    }
  }
}
```

When it comes to building a custom color palette, you can either [curate your colors](https://v2.tailwindcss.com/docs/customizing-colors#curating-colors) from our extensive included color palette, or [configure your own custom colors](https://v2.tailwindcss.com/docs/customizing-colors#custom-colors) by adding your specific color values directly.

* * *

## [Anchor](https://v2.tailwindcss.com/docs/customizing-colors\#curating-colors) Curating colors

If you don’t have a set of completely custom colors in mind for your project, you can curate your colors from our complete color palette by importing `'tailwindcss/colors'` into your config file and choosing the colors you like.

```js
// tailwind.config.js
const colors = require('tailwindcss/colors')

module.exports = {
  theme: {
    colors: {
      transparent: 'transparent',
      current: 'currentColor',
      black: colors.black,
      white: colors.white,
      gray: colors.trueGray,
      indigo: colors.indigo,
      red: colors.rose,
      yellow: colors.amber,
    }
  }
}
```

Don’t forget to include `transparent` and `current` if you’d like those available in your project.

Although each color has a specific name, you’re encouraged to alias them however you like in your own projects. We even do this in the default configuration, aliasing `coolGray` to `gray`, `violet` to `purple`, `amber` to `yellow`, and `emerald` to `green`.

See our [complete color palette reference](https://v2.tailwindcss.com/docs/customizing-colors#color-palette-reference) to see the colors that are available to choose from by default.

* * *

## [Anchor](https://v2.tailwindcss.com/docs/customizing-colors\#custom-colors) Custom colors

You can build a completely custom palette by adding your own color values from scratch:

```js
// tailwind.config.js
module.exports = {
  theme: {
    colors: {
      transparent: 'transparent',
      current: 'currentColor',
      blue: {
        light: '#85d7ff',
        DEFAULT: '#1fb6ff',
        dark: '#009eeb',
      },
      pink: {
        light: '#ff7ce5',
        DEFAULT: '#ff49db',
        dark: '#ff16d1',
      },
      gray: {
        darkest: '#1f2d3d',
        dark: '#3c4858',
        DEFAULT: '#c0ccda',
        light: '#e0e6ed',
        lightest: '#f9fafc',
      }
    }
  }
}
```

By default, these colors are automatically shared by all color-driven utilities, like `textColor`, `backgroundColor`, `borderColor`, and more.

* * *

## [Anchor](https://v2.tailwindcss.com/docs/customizing-colors\#color-object-syntax) Color object syntax

You can see above that we’ve defined our colors using a nested object notation where the nested keys are added to the base color name as modifiers:

```js
// tailwind.config.js
module.exports = {
  theme: {
    colors: {
      indigo: {
        light: '#b3bcf5',
        DEFAULT: '#5c6ac4',
        dark: '#202e78',
      }
    }
  }
}
```

The different segments of the color name are combined to form class names like `bg-indigo-light`.

Like many other places in Tailwind, the `DEFAULT` key is special and means “no modifier”, so this configuration would generate classes like `text-indigo` and `bg-indigo`, not `text-indigo-DEFAULT` or `bg-indigo-DEFAULT`.

You can also define your colors as simple strings instead of objects:

```js
// tailwind.config.js
module.exports = {
  theme: {
    colors: {
      'indigo-lighter': '#b3bcf5',
      'indigo': '#5c6ac4',
      'indigo-dark': '#202e78',
    }
  }
}
```

Note that when accessing colors using the `theme()` function you need to use the same notation you used to define them.

```js
// tailwind.config.js
module.exports = {
  theme: {
    colors: {
      indigo: {
        // theme('colors.indigo.light')
        light: '#b3bcf5',

        // theme('colors.indigo.DEFAULT')
        DEFAULT: '#5c6ac4',
      },

      // theme('colors.indigo-dark')
      'indigo-dark': '#202e78',
    }
  }
}
```

* * *

## [Anchor](https://v2.tailwindcss.com/docs/customizing-colors\#extending-the-defaults) Extending the defaults

As described in the [theme documentation](https://v2.tailwindcss.com/docs/theme#extending-the-default-theme), if you’d like to extend the default color palette rather than override it, you can do so using the `theme.extend.colors` section of your `tailwind.config.js` file:

```js
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        'regal-blue': '#243c5a',
      }
    }
  }
}
```

This will generate classes like `bg-regal-blue` in addition to all of Tailwind’s default colors.

These extensions are merged deeply, so if you’d like to add an additional shade to one of Tailwind’s default colors, you can do so like this:

```js
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        blue: {
          450: '#5F99F7'
        },
      }
    }
  }
}
```

This will add classes like `bg-blue-450` without losing existing classes like `bg-blue-400` or `bg-blue-500`.

* * *

## [Anchor](https://v2.tailwindcss.com/docs/customizing-colors\#disabling-a-default-color) Disabling a default color

If you’d like to disable a default color because you aren’t using it in your project, the easiest approach is to just build a new color palette that doesn’t include the color you’d like to disable.

For example, this `tailwind.config.js` file excludes teal, orange, and pink, but includes the rest of the default colors:

```js
// tailwind.config.js
const colors = require('tailwindcss/colors')

module.exports = {
  theme: {
    colors: {
      transparent: 'transparent',
      current: 'currentColor',
      black: colors.black,
      white: colors.white,
      gray: colors.coolGray,
      red: colors.red,
      yellow: colors.amber,
      blue: colors.blue
    }
  }
}
```

Alternatively, you could leave the color palette untouched and rely on [tree-shaking unused styles](https://v2.tailwindcss.com/docs/optimizing-for-production) to remove the colors you’re not using.

* * *

## [Anchor](https://v2.tailwindcss.com/docs/customizing-colors\#naming-your-colors) Naming your colors

Tailwind uses literal color names _(like red, green, etc.)_ and a numeric scale _(where 50 is light and 900 is dark)_ by default. This ends up being fairly practical for most projects, but there are good reasons to use other naming conventions as well.

For example, if you’re working on a project that needs to support multiple themes, it might make sense to use more abstract names like `primary` and `secondary`:

```js
// tailwind.config.js
module.exports = {
  theme: {
    colors: {
      primary: '#5c6ac4',
      secondary: '#ecc94b',
      // ...
    }
  }
}
```

You can configure those colors explicitly like we have above, or you can pull in colors from our complete color palette and alias them:

```js
// tailwind.config.js
const colors = require('tailwindcss/colors')

module.exports = {
  theme: {
    colors: {
      primary: colors.indigo,
      secondary: colors.yellow,
      neutral: colors.gray,
    }
  }
}
```

You could even define these colors using CSS custom properties (variables) to make it easy to switch themes on the client:

```js
// tailwind.config.js
module.exports = {
  theme: {
    colors: {
      primary: 'var(--color-primary)',
      secondary: 'var(--color-secondary)',
      // ...
    }
  }
}
```

```css
/* In your CSS */
:root {
  --color-primary: #5c6ac4;
  --color-secondary: #ecc94b;
  /* ... */
}

@tailwind base;
@tailwind components;
@tailwind utilities;
```

_Note that colors defined using custom properties will not work with color opacity utilities like `bg-opacity-50` without additional configuration. See [this example repository](https://github.com/adamwathan/tailwind-css-variable-text-opacity-demo) for more information on how to make this work._

* * *

## [Anchor](https://v2.tailwindcss.com/docs/customizing-colors\#generating-colors) Generating colors

A common question we get is “how do I generate the 50–900 shades of my own custom colors?“.

Bad news, color is complicated and despite trying dozens of different tools, we’ve yet to find one that does a good job generating these sorts of color palettes. We picked all of Tailwind’s default colors by hand, meticulously balancing them by eye and testing them in real designs to make sure we were happy with them.

* * *

## [Anchor](https://v2.tailwindcss.com/docs/customizing-colors\#color-palette-reference) Color palette reference

This is a list of all of the colors available when you import `tailwindcss/colors` into your `tailwind.config.js` file.

```js
// tailwind.config.js
const colors = require('tailwindcss/colors')

module.exports = {
  theme: {
    colors: {
      // Build your palette here
      transparent: 'transparent',
      current: 'currentColor',
      gray: colors.trueGray,
      red: colors.red,
      blue: colors.sky,
      yellow: colors.amber,
    }
  }
}
```

Although each color has a specific name, you’re encouraged to alias them however you like in your own projects.

Blue Gray

`colors.blueGray`

50

#F8FAFC

100

#F1F5F9

200

#E2E8F0

300

#CBD5E1

400

#94A3B8

500

#64748B

600

#475569

700

#334155

800

#1E293B

900

#0F172A

Cool Gray

`colors.coolGray`

50

#F9FAFB

100

#F3F4F6

200

#E5E7EB

300

#D1D5DB

400

#9CA3AF

500

#6B7280

600

#4B5563

700

#374151

800

#1F2937

900

#111827

Gray

`colors.gray`

50

#FAFAFA

100

#F4F4F5

200

#E4E4E7

300

#D4D4D8

400

#A1A1AA

500

#71717A

600

#52525B

700

#3F3F46

800

#27272A

900

#18181B

True Gray

`colors.trueGray`

50

#FAFAFA

100

#F5F5F5

200

#E5E5E5

300

#D4D4D4

400

#A3A3A3

500

#737373

600

#525252

700

#404040

800

#262626

900

#171717

Warm Gray

`colors.warmGray`

50

#FAFAF9

100

#F5F5F4

200

#E7E5E4

300

#D6D3D1

400

#A8A29E

500

#78716C

600

#57534E

700

#44403C

800

#292524

900

#1C1917

Red

`colors.red`

50

#FEF2F2

100

#FEE2E2

200

#FECACA

300

#FCA5A5

400

#F87171

500

#EF4444

600

#DC2626

700

#B91C1C

800

#991B1B

900

#7F1D1D

Orange

`colors.orange`

50

#FFF7ED

100

#FFEDD5

200

#FED7AA

300

#FDBA74

400

#FB923C

500

#F97316

600

#EA580C

700

#C2410C

800

#9A3412

900

#7C2D12

Amber

`colors.amber`

50

#FFFBEB

100

#FEF3C7

200

#FDE68A

300

#FCD34D

400

#FBBF24

500

#F59E0B

600

#D97706

700

#B45309

800

#92400E

900

#78350F

Yellow

`colors.yellow`

50

#FEFCE8

100

#FEF9C3

200

#FEF08A

300

#FDE047

400

#FACC15

500

#EAB308

600

#CA8A04

700

#A16207

800

#854D0E

900

#713F12

Lime

`colors.lime`

50

#F7FEE7

100

#ECFCCB

200

#D9F99D

300

#BEF264

400

#A3E635

500

#84CC16

600

#65A30D

700

#4D7C0F

800

#3F6212

900

#365314

Green

`colors.green`

50

#F0FDF4

100

#DCFCE7

200

#BBF7D0

300

#86EFAC

400

#4ADE80

500

#22C55E

600

#16A34A

700

#15803D

800

#166534

900

#14532D

Emerald

`colors.emerald`

50

#ECFDF5

100

#D1FAE5

200

#A7F3D0

300

#6EE7B7

400

#34D399

500

#10B981

600

#059669

700

#047857

800

#065F46

900

#064E3B

Teal

`colors.teal`

50

#F0FDFA

100

#CCFBF1

200

#99F6E4

300

#5EEAD4

400

#2DD4BF

500

#14B8A6

600

#0D9488

700

#0F766E

800

#115E59

900

#134E4A

Cyan

`colors.cyan`

50

#ECFEFF

100

#CFFAFE

200

#A5F3FC

300

#67E8F9

400

#22D3EE

500

#06B6D4

600

#0891B2

700

#0E7490

800

#155E75

900

#164E63

Sky

`colors.sky`

50

#F0F9FF

100

#E0F2FE

200

#BAE6FD

300

#7DD3FC

400

#38BDF8

500

#0EA5E9

600

#0284C7

700

#0369A1

800

#075985

900

#0C4A6E

Blue

`colors.blue`

50

#EFF6FF

100

#DBEAFE

200

#BFDBFE

300

#93C5FD

400

#60A5FA

500

#3B82F6

600

#2563EB

700

#1D4ED8

800

#1E40AF

900

#1E3A8A

Indigo

`colors.indigo`

50

#EEF2FF

100

#E0E7FF

200

#C7D2FE

300

#A5B4FC

400

#818CF8

500

#6366F1

600

#4F46E5

700

#4338CA

800

#3730A3

900

#312E81

Violet

`colors.violet`

50

#F5F3FF

100

#EDE9FE

200

#DDD6FE

300

#C4B5FD

400

#A78BFA

500

#8B5CF6

600

#7C3AED

700

#6D28D9

800

#5B21B6

900

#4C1D95

Purple

`colors.purple`

50

#FAF5FF

100

#F3E8FF

200

#E9D5FF

300

#D8B4FE

400

#C084FC

500

#A855F7

600

#9333EA

700

#7E22CE

800

#6B21A8

900

#581C87

Fuchsia

`colors.fuchsia`

50

#FDF4FF

100

#FAE8FF

200

#F5D0FE

300

#F0ABFC

400

#E879F9

500

#D946EF

600

#C026D3

700

#A21CAF

800

#86198F

900

#701A75

Pink

`colors.pink`

50

#FDF2F8

100

#FCE7F3

200

#FBCFE8

300

#F9A8D4

400

#F472B6

500

#EC4899

600

#DB2777

700

#BE185D

800

#9D174D

900

#831843

Rose

`colors.rose`

50

#FFF1F2

100

#FFE4E6

200

#FECDD3

300

#FDA4AF

400

#FB7185

500

#F43F5E

600

#E11D48

700

#BE123C

800

#9F1239

900

#881337

[←Breakpoints](https://v2.tailwindcss.com/docs/breakpoints) [Spacing→](https://v2.tailwindcss.com/docs/customizing-spacing)

[Edit this page on GitHub](https://github.com/tailwindlabs/tailwindcss.com/edit/master/src/pages/docs/customizing-colors.mdx)

##### On this page

- [Overview](https://v2.tailwindcss.com/docs/customizing-colors#overview)
- [Curating colors](https://v2.tailwindcss.com/docs/customizing-colors#curating-colors)
- [Custom colors](https://v2.tailwindcss.com/docs/customizing-colors#custom-colors)
- [Color object syntax](https://v2.tailwindcss.com/docs/customizing-colors#color-object-syntax)
- [Extending the defaults](https://v2.tailwindcss.com/docs/customizing-colors#extending-the-defaults)
- [Disabling a default color](https://v2.tailwindcss.com/docs/customizing-colors#disabling-a-default-color)
- [Naming your colors](https://v2.tailwindcss.com/docs/customizing-colors#naming-your-colors)
- [Generating colors](https://v2.tailwindcss.com/docs/customizing-colors#generating-colors)
- [Color palette reference](https://v2.tailwindcss.com/docs/customizing-colors#color-palette-reference)