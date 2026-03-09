You're looking at the documentation forTailwind CSS v2.

[Go to Tailwind CSS v3 →](https://tailwindcss.com/)

[Go to Tailwind CSS v3 →](https://tailwindcss.com/)

[Tailwind CSS home page](https://v2.tailwindcss.com/)

Quick search for anythingPress `Ctrl ` and `K` to search

Tailwind CSS Versionv3v2.2.16v1.9.6v0.7.4 [Tailwind CSS on GitHub](https://github.com/tailwindlabs/tailwindcss)

Open site navigation

# Appearance

Utilities for suppressing native form control styling.

## [Anchor](https://v2.tailwindcss.com/docs/appearance\#class-reference) Default class reference

| Class | Properties |
| --- | --- |
| appearance-none | appearance: none; |

## [Anchor](https://v2.tailwindcss.com/docs/appearance\#usage) Usage

Use `appearance-none` to reset any browser specific styling on an element. This utility is often used when creating [custom form components](https://v2.tailwindcss.com/docs/examples/forms).

YesNoMaybe

Default browser styles applied


YesNoMaybe

Default styles removed


```html
<select>
  <option>Yes</option>
  <option>No</option>
  <option>Maybe</option>
</select>

<select class="appearance-none">
  <option>Yes</option>
  <option>No</option>
  <option>Maybe</option>
</select>
```

## [Anchor](https://v2.tailwindcss.com/docs/appearance\#customizing) Customizing

### [Anchor](https://v2.tailwindcss.com/docs/appearance\#variants) Variants

By default, only responsive variants are generated for appearance utilities.

You can control which variants are generated for the appearance utilities by modifying the`appearance` property in the `variants` section of your`tailwind.config.js` file.

For example, this config will also generatehover and focus variants:

```diff
  // tailwind.config.js
  module.exports = {
    variants: {
      extend: {
        // ...
+       appearance: ['hover', 'focus'],
      }
    }
  }
```

### [Anchor](https://v2.tailwindcss.com/docs/appearance\#disabling) Disabling

If you don't plan to use the appearance utilities in your project, you can disable them entirely by setting the`appearance`property to `false` in the`corePlugins` section of your config file:

```diff
  // tailwind.config.js
  module.exports = {
    corePlugins: {
      // ...
+     appearance: false,
    }
  }
```

[←Skew](https://v2.tailwindcss.com/docs/skew) [Cursor→](https://v2.tailwindcss.com/docs/cursor)

[Edit this page on GitHub](https://github.com/tailwindlabs/tailwindcss.com/edit/master/src/pages/docs/appearance.mdx)

##### On this page

- [Default class reference](https://v2.tailwindcss.com/docs/appearance#class-reference)
- [Usage](https://v2.tailwindcss.com/docs/appearance#usage)
- [Customizing](https://v2.tailwindcss.com/docs/appearance#customizing)
- [Variants](https://v2.tailwindcss.com/docs/appearance#variants)
- [Disabling](https://v2.tailwindcss.com/docs/appearance#disabling)