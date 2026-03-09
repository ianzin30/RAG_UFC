You're looking at the documentation forTailwind CSS v2.

[Go to Tailwind CSS v3 →](https://tailwindcss.com/)

[Go to Tailwind CSS v3 →](https://tailwindcss.com/)

[Tailwind CSS home page](https://v2.tailwindcss.com/)

Quick search for anythingPress `Ctrl ` and `K` to search

Tailwind CSS Versionv3v2.2.16v1.9.6v0.7.4 [Tailwind CSS on GitHub](https://github.com/tailwindlabs/tailwindcss)

Open site navigation

# Skew

Utilities for skewing elements with transform.

## [Anchor](https://v2.tailwindcss.com/docs/skew\#class-reference) Default class reference

| Class | Properties |
| --- | --- |
| skew-x-0 | --tw-skew-x: 0deg; |
| skew-x-1 | --tw-skew-x: 1deg; |
| skew-x-2 | --tw-skew-x: 2deg; |
| skew-x-3 | --tw-skew-x: 3deg; |
| skew-x-6 | --tw-skew-x: 6deg; |
| skew-x-12 | --tw-skew-x: 12deg; |
| -skew-x-12 | --tw-skew-x: -12deg; |
| -skew-x-6 | --tw-skew-x: -6deg; |
| -skew-x-3 | --tw-skew-x: -3deg; |
| -skew-x-2 | --tw-skew-x: -2deg; |
| -skew-x-1 | --tw-skew-x: -1deg; |
| skew-y-0 | --tw-skew-y: 0deg; |
| skew-y-1 | --tw-skew-y: 1deg; |
| skew-y-2 | --tw-skew-y: 2deg; |
| skew-y-3 | --tw-skew-y: 3deg; |
| skew-y-6 | --tw-skew-y: 6deg; |
| skew-y-12 | --tw-skew-y: 12deg; |
| -skew-y-12 | --tw-skew-y: -12deg; |
| -skew-y-6 | --tw-skew-y: -6deg; |
| -skew-y-3 | --tw-skew-y: -3deg; |
| -skew-y-2 | --tw-skew-y: -2deg; |
| -skew-y-1 | --tw-skew-y: -1deg; |

## [Anchor](https://v2.tailwindcss.com/docs/skew\#usage) Usage

Skew an element by first enabling transforms with the `transform` utility, then specifying the skew angle using the `skew-x-{amount}` and `skew-y-{amount}` utilities.

![](https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=facearea&facepad=2&w=256&h=256&q=80)

![](https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=facearea&facepad=2&w=256&h=256&q=80)

![](https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=facearea&facepad=2&w=256&h=256&q=80)

![](https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=facearea&facepad=2&w=256&h=256&q=80)

```html
<img class="transform skew-y-0 ...">
<img class="transform skew-y-3 ...">
<img class="transform skew-y-6 ...">
<img class="transform skew-y-12 ...">
```

## [Anchor](https://v2.tailwindcss.com/docs/skew\#responsive) Responsive

To control the skew of an element at a specific breakpoint, add a `{screen}:` prefix to any existing skew utility. For example, use `md:skew-6` to apply the `skew-6` utility at only medium screen sizes and above.

```html
<div class="transform md:skew-6 ..."></div>
```

For more information about Tailwind’s responsive design features, check out the [Responsive Design](https://v2.tailwindcss.com/docs/responsive-design) documentation.

## [Anchor](https://v2.tailwindcss.com/docs/skew\#customizing) Customizing

### [Anchor](https://v2.tailwindcss.com/docs/skew\#skew-scale) Skew scale

By default, Tailwind provides seven general purpose skew utilities. You change, add, or remove these by customizing the `skew` section of your Tailwind theme config.

```diff-js
  // tailwind.config.js
  module.exports = {
    theme: {
      extend: {
        skew: {
+         '25': '25deg',
+         '60': '60deg',
        }
      }
    }
  }
```

Learn more about customizing the default theme in the [theme customization documentation](https://v2.tailwindcss.com/docs/theme#customizing-the-default-theme).

### [Anchor](https://v2.tailwindcss.com/docs/skew\#variants) Variants

By default, only responsive, hover and focus variants are generated for skew utilities.

You can control which variants are generated for the skew utilities by modifying the`skew` property in the `variants` section of your`tailwind.config.js` file.

For example, this config will also generateactive and group-hover variants:

```diff
  // tailwind.config.js
  module.exports = {
    variants: {
      extend: {
        // ...
+       skew: ['active', 'group-hover'],
      }
    }
  }
```

### [Anchor](https://v2.tailwindcss.com/docs/skew\#disabling) Disabling

If you don't plan to use the skew utilities in your project, you can disable them entirely by setting the`skew`property to `false` in the`corePlugins` section of your config file:

```diff
  // tailwind.config.js
  module.exports = {
    corePlugins: {
      // ...
+     skew: false,
    }
  }
```

[←Translate](https://v2.tailwindcss.com/docs/translate) [Appearance→](https://v2.tailwindcss.com/docs/appearance)

[Edit this page on GitHub](https://github.com/tailwindlabs/tailwindcss.com/edit/master/src/pages/docs/skew.mdx)

##### On this page

- [Default class reference](https://v2.tailwindcss.com/docs/skew#class-reference)
- [Usage](https://v2.tailwindcss.com/docs/skew#usage)
- [Responsive](https://v2.tailwindcss.com/docs/skew#responsive)
- [Customizing](https://v2.tailwindcss.com/docs/skew#customizing)
- [Skew scale](https://v2.tailwindcss.com/docs/skew#skew-scale)
- [Variants](https://v2.tailwindcss.com/docs/skew#variants)
- [Disabling](https://v2.tailwindcss.com/docs/skew#disabling)