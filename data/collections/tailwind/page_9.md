You're looking at the documentation forTailwind CSS v2.

[Go to Tailwind CSS v3 →](https://tailwindcss.com/)

[Go to Tailwind CSS v3 →](https://tailwindcss.com/)

[Tailwind CSS home page](https://v2.tailwindcss.com/)

Quick search for anythingPress `Ctrl ` and `K` to search

Tailwind CSS Versionv3v2.2.16v1.9.6v0.7.4 [Tailwind CSS on GitHub](https://github.com/tailwindlabs/tailwindcss)

Open site navigation

# Isolation

Tailwind CSS versionv2.1+

Utilities for controlling whether an element should explicitly create a new stacking context.

## [Anchor](https://v2.tailwindcss.com/docs/isolation\#class-reference) Default class reference

| Class | Properties |
| --- | --- |
| isolate | isolation: isolate; |
| isolation-auto | isolation: auto; |

## [Anchor](https://v2.tailwindcss.com/docs/isolation\#usage) Usage

Use the `isolate` and `isolation-auto` utilities to control whether an element should explicitly create a new stacking context.

```html
<div class="isolate ...">
  <!-- ... -->
</div>
```

## [Anchor](https://v2.tailwindcss.com/docs/isolation\#responsive) Responsive

To control the isolation property at a specific breakpoint, add a `{screen}:` prefix to any existing isolation utility. For example, use `md:isolation-auto` to apply the `isolation-auto` utility at only medium screen sizes and above.

```html
<div class="isolate md:isolation-auto ...">
  <!-- ... -->
</div>
```

For more information about Tailwind’s responsive design features, check out the [Responsive Design](https://v2.tailwindcss.com/docs/responsive-design) documentation.

## [Anchor](https://v2.tailwindcss.com/docs/isolation\#customizing) Customizing

### [Anchor](https://v2.tailwindcss.com/docs/isolation\#variants) Variants

By default, only responsive variants are generated for isolation utilities.

You can control which variants are generated for the isolation utilities by modifying the`isolation` property in the `variants` section of your`tailwind.config.js` file.

For example, this config will also generatehover and focus variants:

```diff
  // tailwind.config.js
  module.exports = {
    variants: {
      extend: {
        // ...
+       isolation: ['hover', 'focus'],
      }
    }
  }
```

### [Anchor](https://v2.tailwindcss.com/docs/isolation\#disabling) Disabling

If you don't plan to use the isolation utilities in your project, you can disable them entirely by setting the`isolation`property to `false` in the`corePlugins` section of your config file:

```diff
  // tailwind.config.js
  module.exports = {
    corePlugins: {
      // ...
+     isolation: false,
    }
  }
```

[←Clear](https://v2.tailwindcss.com/docs/clear) [Object Fit→](https://v2.tailwindcss.com/docs/object-fit)

[Edit this page on GitHub](https://github.com/tailwindlabs/tailwindcss.com/edit/master/src/pages/docs/isolation.mdx)

##### On this page

- [Default class reference](https://v2.tailwindcss.com/docs/isolation#class-reference)
- [Usage](https://v2.tailwindcss.com/docs/isolation#usage)
- [Responsive](https://v2.tailwindcss.com/docs/isolation#responsive)
- [Customizing](https://v2.tailwindcss.com/docs/isolation#customizing)
- [Variants](https://v2.tailwindcss.com/docs/isolation#variants)
- [Disabling](https://v2.tailwindcss.com/docs/isolation#disabling)