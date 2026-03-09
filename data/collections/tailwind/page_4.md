You're looking at the documentation forTailwind CSS v2.

[Go to Tailwind CSS v3 →](https://tailwindcss.com/)

[Go to Tailwind CSS v3 →](https://tailwindcss.com/)

[Tailwind CSS home page](https://v2.tailwindcss.com/)

Quick search for anythingPress `Ctrl ` and `K` to search

Tailwind CSS Versionv3v2.2.16v1.9.6v0.7.4 [Tailwind CSS on GitHub](https://github.com/tailwindlabs/tailwindcss)

Open site navigation

# Outline

Utilities for controlling an element's outline.

## [Anchor](https://v2.tailwindcss.com/docs/outline\#class-reference) Default class reference

| Class | Properties |
| --- | --- |
| outline-none | outline: 2px solid transparent;<br>outline-offset: 2px; |
| outline-white | outline: 2px dotted white;<br>outline-offset: 2px; |
| outline-black | outline: 2px dotted black;<br>outline-offset: 2px; |

## [Anchor](https://v2.tailwindcss.com/docs/outline\#remove-outlines) Remove outlines

Use `outline-none` to hide the default browser outline on focused elements.

It is highly recommended to apply your own focus styling for accessibility when using this utility.

```html
<input type="text"
  placeholder="Default focus style"
  class="..." />

<input type="text"
  placeholder="Custom focus style"
  class="focus:outline-none focus:ring focus:border-blue-300 ..." />
```

The `outline-none` utility is implemented using a transparent outline under the hood to ensure elements are still visibly focused to [Windows high contrast mode](https://blogs.windows.com/msedgedev/2020/09/17/styling-for-windows-high-contrast-with-new-standards-for-forced-colors/) users.

## [Anchor](https://v2.tailwindcss.com/docs/outline\#dotted-outlines) Dotted outlines

Use the `outline-white` and `outline-black` utilities to add a 2px dotted border around an element with a 2px offset. These are useful as an accessible general purpose custom focus style if you don’t want to design your own.

Button A

Button B

```html
<button class="focus:outline-black ...">Button A</button>
<button class="focus:outline-white ...">Button B</button>
```

## [Anchor](https://v2.tailwindcss.com/docs/outline\#customizing) Customizing

### [Anchor](https://v2.tailwindcss.com/docs/outline\#outlines) Outlines

By default, Tailwind provides three outline utilities. You can customize these by editing the `theme.outline` section of your `tailwind.config.js` file.

```js
  // tailwind.config.js
  module.exports = {
    theme: {
      extend: {
        outline: {
          blue: '2px solid #0000ff',
        }
      }
    }
  }
```

You can also provide an `outline-offset` value for any custom outline utilities using a tuple of the form `[outline, outlineOffset]`:

```js
  // tailwind.config.js
  module.exports = {
    theme: {
      extend: {
        outline: {
          blue: ['2px solid #0000ff', '1px'],
        }
      }
    }
  }
```

### [Anchor](https://v2.tailwindcss.com/docs/outline\#variants) Variants

By default, only responsive, focus-within and focus variants are generated for outline utilities.

You can control which variants are generated for the outline utilities by modifying the`outline` property in the `variants` section of your`tailwind.config.js` file.

For example, this config will also generatehover and active variants:

```diff
  // tailwind.config.js
  module.exports = {
    variants: {
      extend: {
        // ...
+       outline: ['hover', 'active'],
      }
    }
  }
```

### [Anchor](https://v2.tailwindcss.com/docs/outline\#disabling) Disabling

If you don't plan to use the outline utilities in your project, you can disable them entirely by setting the`outline`property to `false` in the`corePlugins` section of your config file:

```diff
  // tailwind.config.js
  module.exports = {
    corePlugins: {
      // ...
+     outline: false,
    }
  }
```

[←Cursor](https://v2.tailwindcss.com/docs/cursor) [Pointer Events→](https://v2.tailwindcss.com/docs/pointer-events)

[Edit this page on GitHub](https://github.com/tailwindlabs/tailwindcss.com/edit/master/src/pages/docs/outline.mdx)

##### On this page

- [Default class reference](https://v2.tailwindcss.com/docs/outline#class-reference)
- [Remove outlines](https://v2.tailwindcss.com/docs/outline#remove-outlines)
- [Dotted outlines](https://v2.tailwindcss.com/docs/outline#dotted-outlines)
- [Customizing](https://v2.tailwindcss.com/docs/outline#customizing)
- [Outlines](https://v2.tailwindcss.com/docs/outline#outlines)
- [Variants](https://v2.tailwindcss.com/docs/outline#variants)
- [Disabling](https://v2.tailwindcss.com/docs/outline#disabling)