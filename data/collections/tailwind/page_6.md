You're looking at the documentation forTailwind CSS v2.

[Go to Tailwind CSS v3 →](https://tailwindcss.com/)

[Go to Tailwind CSS v3 →](https://tailwindcss.com/)

[Tailwind CSS home page](https://v2.tailwindcss.com/)

Quick search for anythingPress `Ctrl ` and `K` to search

Tailwind CSS Versionv3v2.2.16v1.9.6v0.7.4 [Tailwind CSS on GitHub](https://github.com/tailwindlabs/tailwindcss)

Open site navigation

# Configuration

A guide to configuring and customizing your Tailwind installation.

Because Tailwind is a framework for building bespoke user interfaces, it has been designed from the ground up with customization in mind.

By default, Tailwind will look for an optional `tailwind.config.js` file at the root of your project where you can define any customizations.

```js
// Example `tailwind.config.js` file
const colors = require('tailwindcss/colors')

module.exports = {
  theme: {
    colors: {
      gray: colors.coolGray,
      blue: colors.lightBlue,
      red: colors.rose,
      pink: colors.fuchsia,
    },
    fontFamily: {
      sans: ['Graphik', 'sans-serif'],
      serif: ['Merriweather', 'serif'],
    },
    extend: {
      spacing: {
        '128': '32rem',
        '144': '36rem',
      },
      borderRadius: {
        '4xl': '2rem',
      }
    }
  },
  variants: {
    extend: {
      borderColor: ['focus-visible'],
      opacity: ['disabled'],
    }
  }
}
```

Every section of the config file is optional, so you only have to specify what you’d like to change. Any missing sections will fall back to Tailwind’s [default configuration](https://github.com/tailwindlabs/tailwindcss/blob/v2.2.19/stubs/defaultConfig.stub.js).

## [Anchor](https://v2.tailwindcss.com/docs/configuration\#creating-your-configuration-file) Creating your configuration file

Generate a Tailwind config file for your project using the Tailwind CLI utility included when you install the `tailwindcss` npm package:

```shell
npx tailwindcss init
```

This will create a minimal `tailwind.config.js` file at the root of your project:

```js
// tailwind.config.js
module.exports = {
  purge: [],
  darkMode: false, // or 'media' or 'class'
  theme: {
    extend: {},
  },
  variants: {
    extend: {},
  },
  plugins: [],
}
```

### [Anchor](https://v2.tailwindcss.com/docs/configuration\#using-a-different-file-name) Using a different file name

To use a name other than `tailwind.config.js`, pass it as an argument on the command-line:

```shell
npx tailwindcss init tailwindcss-config.js
```

If you use a custom file name, you will need to specify it when including Tailwind as a plugin in your PostCSS configuration as well:

```js
// postcss.config.js
module.exports = {
  plugins: {
    tailwindcss: { config: './tailwindcss-config.js' },
  },
}
```

### [Anchor](https://v2.tailwindcss.com/docs/configuration\#generating-a-post-css-configuration-file) Generating a PostCSS configuration file

Use the `-p` flag if you’d like to also generate a basic `postcss.config.js` file alongside your `tailwind.config.js` file:

```shell
npx tailwindcss init -p
```

This will generate a `postcss.config.js` file in your project that looks like this:

```js
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

### [Anchor](https://v2.tailwindcss.com/docs/configuration\#scaffolding-the-entire-default-configuration) Scaffolding the entire default configuration

For most users we encourage you to keep your config file as minimal as possible, and only specify the things you want to customize.

If you’d rather scaffold a complete configuration file that includes all of Tailwind’s default configuration, use the `--full` option:

```shell
npx tailwindcss init --full
```

You’ll get a file that matches the [default configuration file](https://unpkg.com/browse/tailwindcss@2.2.19/stubs/defaultConfig.stub.js) Tailwind uses internally.

## [Anchor](https://v2.tailwindcss.com/docs/configuration\#theme) Theme

The `theme` section is where you define your color palette, fonts, type scale, border sizes, breakpoints — anything related to the visual design of your site.

```js
// tailwind.config.js
module.exports = {
  theme: {
    colors: {
      gray: colors.coolGray,
      blue: colors.lightBlue,
      red: colors.rose,
      pink: colors.fuchsia,
    },
    fontFamily: {
      sans: ['Graphik', 'sans-serif'],
      serif: ['Merriweather', 'serif'],
    },
    extend: {
      spacing: {
        '128': '32rem',
        '144': '36rem',
      },
      borderRadius: {
        '4xl': '2rem',
      }
    }
  }
}
```

Learn more about the default theme and how to customize it in the [theme configuration guide](https://v2.tailwindcss.com/docs/theme).

## [Anchor](https://v2.tailwindcss.com/docs/configuration\#variants) Variants

The `variants` section lets you control which [variants](https://v2.tailwindcss.com/docs/hover-focus-and-other-states) are generated for each core utility plugin.

```js
// tailwind.config.js
module.exports = {
  variants: {
    fill: [],
    extend: {
      borderColor: ['focus-visible'],
      opacity: ['disabled'],
    }
  },
}
```

Learn more in the [variants configuration guide](https://v2.tailwindcss.com/docs/configuring-variants).

## [Anchor](https://v2.tailwindcss.com/docs/configuration\#plugins) Plugins

The `plugins` section allows you to register plugins with Tailwind that can be used to generate extra utilities, components, base styles, or custom variants.

```js
// tailwind.config.js
module.exports = {
  plugins: [\
    require('@tailwindcss/forms'),\
    require('@tailwindcss/aspect-ratio'),\
    require('@tailwindcss/typography'),\
    require('tailwindcss-children'),\
  ],
}
```

Learn more about writing your own plugins in the [plugin authoring guide](https://v2.tailwindcss.com/docs/plugins).

## [Anchor](https://v2.tailwindcss.com/docs/configuration\#presets) Presets

The `presets` section allows you to specify your own custom base configuration instead of using Tailwind’s default base configuration.

```js
// tailwind.config.js
module.exports = {
  presets: [\
    require('@acmecorp/base-tailwind-config')\
  ],

  // Project-specific customizations
  theme: {
    //...
  },
  // ...
}
```

Learn more about presets in the [presets documentation](https://v2.tailwindcss.com/docs/presets).

## [Anchor](https://v2.tailwindcss.com/docs/configuration\#prefix) Prefix

The `prefix` option allows you to add a custom prefix to all of Tailwind’s generated utility classes. This can be really useful when layering Tailwind on top of existing CSS where there might be naming conflicts.

For example, you could add a `tw-` prefix by setting the `prefix` option like so:

```js
// tailwind.config.js
module.exports = {
  prefix: 'tw-',
}
```

Now every class will be generated with the configured prefix:

```css
.tw-text-left {
  text-align: left;
}
.tw-text-center {
  text-align: center;
}
.tw-text-right {
  text-align: right;
}
/* etc. */
```

It’s important to understand that this prefix is added _after_ any variant prefixes. That means that classes with responsive or state prefixes like `sm:` or `hover:` will still have the responsive or state prefix _first_, with your custom prefix appearing after the colon:

```html
<div class="tw-text-lg md:tw-text-xl tw-bg-red-500 hover:tw-bg-blue-500">
  <!-- -->
</div>
```

Prefixes are only added to classes generated by Tailwind; **no prefix will be added to your own custom classes.**

That means if you add your own responsive utility like this:

```css
@variants hover {
  .bg-brand-gradient { /* ... */ }
}
```

…the generated responsive classes will not have your configured prefix:

```css
.bg-brand-gradient { /* ... */ }
.hover\:bg-brand-gradient:hover { /* ... */ }
```

If you’d like to prefix your own utilities as well, just add the prefix to the class definition:

```css
@variants hover {
  .tw-bg-brand-gradient { /* ... */ }
}
```

## [Anchor](https://v2.tailwindcss.com/docs/configuration\#important) Important

The `important` option lets you control whether or not Tailwind’s utilities should be marked with `!important`. This can be really useful when using Tailwind with existing CSS that has high specificity selectors.

To generate utilities as `!important`, set the `important` key in your configuration options to `true`:

```js
// tailwind.config.js
module.exports = {
  important: true,
}
```

Now all of Tailwind’s utility classes will be generated as `!important`:

```css
.leading-none {
  line-height: 1 !important;
}
.leading-tight {
  line-height: 1.25 !important;
}
.leading-snug {
  line-height: 1.375 !important;
}
/* etc. */
```

Note that any of your own custom utilities **will not** automatically be marked as `!important` by enabling this option.

If you’d like to make your own utilities `!important`, just add `!important` to the end of each declaration yourself:

```css
@responsive {
  .bg-brand-gradient {
    background-image: linear-gradient(#3490dc, #6574cd) !important;
  }
}
```

### [Anchor](https://v2.tailwindcss.com/docs/configuration\#selector-strategy) Selector strategy

Setting `important` to `true` can introduce some issues when incorporating third-party JS libraries that add inline styles to your elements. In those cases, Tailwind’s `!important` utilities defeat the inline styles, which can break your intended design.

To get around this, you can set `important` to an ID selector like `#app` instead:

```js
// tailwind.config.js
module.exports = {
  important: '#app',
}
```

This configuration will prefix all of your utilities with the given selector, effectively increasing their specificity without actually making them `!important`.

After you specify the `important` selector, you’ll need to ensure that the root element of your site matches it. Using the example above, we would need to set our root element’s `id` attribute to `app` in order for styles to work properly.

After your configuration is all set up and your root element matches the selector in your Tailwind config, all of Tailwind’s utilities will have a high enough specificity to defeat other classes used in your project, **without** interfering with inline styles:

```html
<html>
<!-- ... -->
<style>
  .high-specificity .nested .selector {
    color: blue;
  }
</style>
<body id="app">
  <div class="high-specificity">
    <div class="nested">
      <!-- Will be red-500 -->
      <div class="selector text-red-500"><!-- ... --></div>
    </div>
  </div>

  <!-- Will be #bada55 -->
  <div class="text-red-500" style="color: #bada55;"><!-- ... --></div>
</body>
</html>
```

When using the selector strategy, be sure that the template file that includes your root selector is included in your [purge configuration](https://v2.tailwindcss.com/docs/optimizing-for-production#basic-usage), otherwise all of your CSS will be removed when building for production.

## [Anchor](https://v2.tailwindcss.com/docs/configuration\#separator) Separator

The `separator` option lets you customize what character or string should be used to separate variant prefixes (screen sizes, `hover`, `focus`, etc.) from utility names (`text-center`, `items-end`, etc.).

We use a colon by default (`:`), but it can be useful to change this if you’re using a templating language like [Pug](https://pugjs.org/) that doesn’t support special characters in class names.

```js
// tailwind.config.js
module.exports = {
  separator: '_',
}
```

## [Anchor](https://v2.tailwindcss.com/docs/configuration\#variant-order) Variant Order

If you are using the `extend` feature to enable extra variants, those variants are automatically sorted to respect a sensible default variant order.

You can customize this if necessary under the `variantOrder` key:

```js
// tailwind.config.js
module.exports = {
  // ...
  variantOrder: [\
    'first',\
    'last',\
    'odd',\
    'even',\
    'visited',\
    'checked',\
    'group-hover',\
    'group-focus',\
    'focus-within',\
    'hover',\
    'focus',\
    'focus-visible',\
    'active',\
    'disabled',\
  ]
}
```

## [Anchor](https://v2.tailwindcss.com/docs/configuration\#core-plugins) Core Plugins

The `corePlugins` section lets you completely disable classes that Tailwind would normally generate by default if you don’t need them for your project.

If you don’t provide any `corePlugins` configuration, all core plugins will be enabled by default:

```js
// tailwind.config.js
module.exports = {
  // ...
}
```

If you’d like to disable specific core plugins, provide an object for `corePlugins` that sets those plugins to `false`:

```js
// tailwind.config.js
module.exports = {
  corePlugins: {
    float: false,
    objectFit: false,
    objectPosition: false,
  }
}
```

If you’d like to safelist which core plugins should be enabled, provide an array that includes a list of the core plugins you’d like to use:

```js
// tailwind.config.js
module.exports = {
  corePlugins: [\
    'margin',\
    'padding',\
    'backgroundColor',\
    // ...\
  ]
}
```

If you’d like to disable all of Tailwind’s core plugins and simply use Tailwind as a tool for processing your own custom plugins, provide an empty array:

```js
// tailwind.config.js
module.exports = {
  corePlugins: []
}
```

Here’s a list of every core plugin for reference:

| Core Plugin | Description |
| --- | --- |
| `preflight` | Tailwind's base/reset styles |
| `container` | The `container` component |
| `accessibility` | The `sr-only` and `not-sr-only` utilities |
| `alignContent` | The`align-content`utilities like `content-end` |
| `alignItems` | The`align-items`utilities like `items-center` |
| `alignSelf` | The`align-self`utilities like `self-end` |
| `animation` | The`animation`utilities like `` |
| `appearance` | The`appearance`utilities like `appearance-none` |
| `backdropBlur` | The`backdrop-blur`utilities like `` |
| `backdropBrightness` | The`backdrop-brightness`utilities like `` |
| `backdropContrast` | The`backdrop-contrast`utilities like `` |
| `backdropFilter` | The`backdrop-filter`utilities like `backdrop-filter` |
| `backdropGrayscale` | The`backdrop-grayscale`utilities like `` |
| `backdropHueRotate` | The`backdrop-hue-rotate`utilities like `` |
| `backdropInvert` | The`backdrop-invert`utilities like `` |
| `backdropOpacity` | The`backdrop-opacity`utilities like `` |
| `backdropSaturate` | The`backdrop-saturate`utilities like `` |
| `backdropSepia` | The`backdrop-sepia`utilities like `` |
| `backgroundAttachment` | The`background-attachment`utilities like `bg-local` |
| `backgroundBlendMode` | The`background-blend-mode`utilities like `bg-blend-color-burn` |
| `backgroundClip` | The`background-clip`utilities like `bg-clip-padding` |
| `backgroundColor` | The`background-color`utilities like `` |
| `backgroundImage` | The`background-image`utilities like `` |
| `backgroundOpacity` | The `background-color` opacity utilities like `bg-opacity-25` |
| `backgroundOrigin` | The`background-origin`utilities like `bg-origin-padding` |
| `backgroundPosition` | The`background-position`utilities like `` |
| `backgroundRepeat` | The`background-repeat`utilities like `bg-repeat-x` |
| `backgroundSize` | The`background-size`utilities like `` |
| `blur` | The`blur`utilities like `` |
| `borderCollapse` | The`border-collapse`utilities like `border-collapse` |
| `borderColor` | The`border-color`utilities like `` |
| `borderOpacity` | The `border-color` opacity utilities like `border-opacity-25` |
| `borderRadius` | The`border-radius`utilities like `` |
| `borderStyle` | The`border-style`utilities like `border-dotted` |
| `borderWidth` | The`border-width`utilities like `` |
| `boxDecorationBreak` | The`box-decoration-break`utilities like `decoration-slice` |
| `boxShadow` | The`box-shadow`utilities like `,` |
| `boxSizing` | The`box-sizing`utilities like `box-border` |
| `brightness` | The`brightness`utilities like `` |
| `caretColor` | The`caret-color`utilities like `` |
| `clear` | The`clear`utilities like `clear-right` |
| `content` | The`content`utilities like `` |
| `contrast` | The`contrast`utilities like `` |
| `cursor` | The`cursor`utilities like `` |
| `display` | The`display`utilities like `table-column-group` |
| `divideColor` | The between elements `border-color` utilities like `divide-gray-500` |
| `divideOpacity` | The`divide-opacity`utilities like `` |
| `divideStyle` | The`divide-style`utilities like `divide-dotted` |
| `divideWidth` | The between elements `border-width` utilities like `divide-x-2` |
| `dropShadow` | The`drop-shadow`utilities like `drop-shadow-lg` |
| `fill` | The`fill`utilities like `` |
| `filter` | The`filter`utilities like `filter` |
| `flex` | The`flex`utilities like `` |
| `flexDirection` | The`flex-direction`utilities like `flex-row-reverse` |
| `flexGrow` | The`flex-grow`utilities like `` |
| `flexShrink` | The`flex-shrink`utilities like `` |
| `flexWrap` | The`flex-wrap`utilities like `flex-wrap-reverse` |
| `float` | The`float`utilities like `float-left` |
| `fontFamily` | The`font-family`utilities like `` |
| `fontSize` | The`font-size`utilities like `` |
| `fontSmoothing` | The`font-smoothing`utilities like `antialiased` |
| `fontStyle` | The`font-style`utilities like `italic` |
| `fontVariantNumeric` | The`font-variant-numeric`utilities like `lining-nums` |
| `fontWeight` | The`font-weight`utilities like `` |
| `gap` | The`gap`utilities like `` |
| `gradientColorStops` | The`gradient-color-stops`utilities like `` |
| `grayscale` | The`grayscale`utilities like `` |
| `gridAutoColumns` | The`grid-auto-columns`utilities like `` |
| `gridAutoFlow` | The`grid-auto-flow`utilities like `grid-flow-col` |
| `gridAutoRows` | The`grid-auto-rows`utilities like `` |
| `gridColumn` | The`grid-column`utilities like `` |
| `gridColumnEnd` | The`grid-column-end`utilities like `` |
| `gridColumnStart` | The`grid-column-start`utilities like `` |
| `gridRow` | The`grid-row`utilities like `` |
| `gridRowEnd` | The`grid-row-end`utilities like `` |
| `gridRowStart` | The`grid-row-start`utilities like `` |
| `gridTemplateColumns` | The`grid-template-columns`utilities like `` |
| `gridTemplateRows` | The`grid-template-rows`utilities like `` |
| `height` | The`height`utilities like `` |
| `hueRotate` | The`hue-rotate`utilities like `` |
| `inset` | The`inset`utilities like `` |
| `invert` | The`invert`utilities like `` |
| `isolation` | The`isolation`utilities like `isolate` |
| `justifyContent` | The`justify-content`utilities like `justify-center` |
| `justifyItems` | The`justify-items`utilities like `justify-items-end` |
| `justifySelf` | The`justify-self`utilities like `justify-self-end` |
| `letterSpacing` | The`letter-spacing`utilities like `` |
| `lineHeight` | The`line-height`utilities like `` |
| `listStylePosition` | The`list-style-position`utilities like `list-inside` |
| `listStyleType` | The`list-style-type`utilities like `` |
| `margin` | The`margin`utilities like `` |
| `maxHeight` | The`max-height`utilities like `` |
| `maxWidth` | The`max-width`utilities like `` |
| `minHeight` | The`min-height`utilities like `` |
| `minWidth` | The`min-width`utilities like `` |
| `mixBlendMode` | The`mix-blend-mode`utilities like `mix-blend-color-burn` |
| `objectFit` | The`object-fit`utilities like `object-fill` |
| `objectPosition` | The`object-position`utilities like `` |
| `opacity` | The`opacity`utilities like `` |
| `order` | The`order`utilities like `` |
| `outline` | The`outline`utilities like `` |
| `overflow` | The`overflow`utilities like `overflow-y-auto` |
| `overscrollBehavior` | The`overscroll-behavior`utilities like `overscroll-y-contain` |
| `padding` | The`padding`utilities like `` |
| `placeContent` | The`place-content`utilities like `place-content-between` |
| `placeholderColor` | The placeholder `color` utilities like `placeholder-red-600` |
| `placeholderOpacity` | The placeholder `color` opacity utilities like `placeholder-opacity-25` |
| `placeItems` | The`place-items`utilities like `place-items-end` |
| `placeSelf` | The`place-self`utilities like `place-self-end` |
| `pointerEvents` | The`pointer-events`utilities like `pointer-events-none` |
| `position` | The`position`utilities like `absolute` |
| `resize` | The`resize`utilities like `resize-y` |
| `ringColor` | The`ring-color`utilities like `` |
| `ringOffsetColor` | The`ring-offset-color`utilities like `` |
| `ringOffsetWidth` | The`ring-offset-width`utilities like `` |
| `ringOpacity` | The`ring-opacity`utilities like `` |
| `ringWidth` | The`ring-width`utilities like `,` |
| `rotate` | The`rotate`utilities like `` |
| `saturate` | The`saturate`utilities like `` |
| `scale` | The`scale`utilities like `` |
| `sepia` | The`sepia`utilities like `` |
| `skew` | The`skew`utilities like `` |
| `space` | The "space-between" utilities like `space-x-4` |
| `stroke` | The`stroke`utilities like `` |
| `strokeWidth` | The`stroke-width`utilities like `` |
| `tableLayout` | The`table-layout`utilities like `table-auto` |
| `textAlign` | The`text-align`utilities like `text-center` |
| `textColor` | The`text-color`utilities like `` |
| `textDecoration` | The`text-decoration`utilities like `line-through` |
| `textOpacity` | The`text-opacity`utilities like `` |
| `textOverflow` | The`text-overflow`utilities like `overflow-ellipsis` |
| `textTransform` | The`text-transform`utilities like `lowercase` |
| `transform` | The `transform` utility (for enabling transform features) |
| `transformOrigin` | The`transform-origin`utilities like `` |
| `transitionDelay` | The`transition-delay`utilities like `` |
| `transitionDuration` | The`transition-duration`utilities like `` |
| `transitionProperty` | The`transition-property`utilities like `` |
| `transitionTimingFunction` | The`transition-timing-function`utilities like `` |
| `translate` | The`translate`utilities like `` |
| `userSelect` | The`user-select`utilities like `select-text` |
| `verticalAlign` | The`vertical-align`utilities like `align-middle` |
| `visibility` | The`visibility`utilities like `visible` |
| `whitespace` | The`whitespace`utilities like `whitespace-pre` |
| `width` | The`width`utilities like `` |
| `wordBreak` | The`word-break`utilities like `break-words` |
| `zIndex` | The`z-index`utilities like `` |

## [Anchor](https://v2.tailwindcss.com/docs/configuration\#referencing-in-java-script) Referencing in JavaScript

It can often be useful to reference your configuration values in your own client-side JavaScript — for example to access some of your theme values when dynamically applying inline styles in a React or Vue component.

To make this easy, Tailwind provides a `resolveConfig` helper you can use to generate a fully merged version of your configuration object:

```js
import resolveConfig from 'tailwindcss/resolveConfig'
import tailwindConfig from './tailwind.config.js'

const fullConfig = resolveConfig(tailwindConfig)

fullConfig.theme.width[4]
// => '1rem'

fullConfig.theme.screens.md
// => '768px'

fullConfig.theme.boxShadow['2xl']
// => '0 25px 50px -12px rgba(0, 0, 0, 0.25)'
```

Note that this will transitively pull in a lot of our build-time dependencies, resulting in bigger bundle client-side size. To avoid this, we recommend using a tool like [babel-plugin-preval](https://github.com/kentcdodds/babel-plugin-preval) to generate a static version of your configuration at build-time.

[←Functions & Directives](https://v2.tailwindcss.com/docs/functions-and-directives) [Just-in-Time Mode→](https://v2.tailwindcss.com/docs/just-in-time-mode)

[Edit this page on GitHub](https://github.com/tailwindlabs/tailwindcss.com/edit/master/src/pages/docs/configuration.mdx)

##### On this page

- [Creating your configuration file](https://v2.tailwindcss.com/docs/configuration#creating-your-configuration-file)
- [Using a different file name](https://v2.tailwindcss.com/docs/configuration#using-a-different-file-name)
- [Generating a PostCSS configuration file](https://v2.tailwindcss.com/docs/configuration#generating-a-post-css-configuration-file)
- [Scaffolding the entire default configuration](https://v2.tailwindcss.com/docs/configuration#scaffolding-the-entire-default-configuration)
- [Theme](https://v2.tailwindcss.com/docs/configuration#theme)
- [Variants](https://v2.tailwindcss.com/docs/configuration#variants)
- [Plugins](https://v2.tailwindcss.com/docs/configuration#plugins)
- [Presets](https://v2.tailwindcss.com/docs/configuration#presets)
- [Prefix](https://v2.tailwindcss.com/docs/configuration#prefix)
- [Important](https://v2.tailwindcss.com/docs/configuration#important)
- [Selector strategy](https://v2.tailwindcss.com/docs/configuration#selector-strategy)
- [Separator](https://v2.tailwindcss.com/docs/configuration#separator)
- [Variant Order](https://v2.tailwindcss.com/docs/configuration#variant-order)
- [Core Plugins](https://v2.tailwindcss.com/docs/configuration#core-plugins)
- [Referencing in JavaScript](https://v2.tailwindcss.com/docs/configuration#referencing-in-java-script)