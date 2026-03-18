Source URL: https://ohmyposh.dev/docs/experimental/streaming

[Skip to main content](https://ohmyposh.dev/docs/experimental/streaming#__docusaurus_skipToContent_fallback)

If you're enjoying Oh My Posh, consider becoming a [sponsor](https://github.com/sponsors/JanDeDobbeleer)
 to keep the project going strong 💪

On this page

Experimental Feature

Streaming is an **experimental beta feature** that is currently under active development. The behavior and configuration may change in future releases. Use with caution in production environments.

What is Streaming?[​](https://ohmyposh.dev/docs/experimental/streaming#what-is-streaming "Direct link to What is Streaming?")

------------------------------------------------------------------------------------------------------------------------------

Streaming is a new rendering mode for Oh My Posh that displays your prompt progressively as segments complete their execution. Instead of waiting for all segments to finish before showing the prompt, streaming mode shows an initial prompt immediately and updates it incrementally as data becomes available.

How Does It Work?[​](https://ohmyposh.dev/docs/experimental/streaming#how-does-it-work "Direct link to How Does It Work?")

---------------------------------------------------------------------------------------------------------------------------

In the traditional rendering mode, Oh My Posh:

1.  Executes all segments (some may take time to fetch data from APIs, run commands, etc.)
2.  Waits for all segments to complete
3.  Renders the complete prompt once
4.  Displays the result

With **streaming mode**, Oh My Posh:

1.  Immediately displays a prompt with fast segments
2.  Shows `...` for segments that are still loading (override using the segment's `placeholder` property)
3.  Progressively updates the prompt as slow segments complete
4.  Re-renders the prompt with updated data

This provides a more responsive experience, especially when you have segments that fetch remote data or perform time-consuming operations.

Enabling Streaming[​](https://ohmyposh.dev/docs/experimental/streaming#enabling-streaming "Direct link to Enabling Streaming")

-------------------------------------------------------------------------------------------------------------------------------

To enable streaming mode, add the `streaming` property to your configuration file and set it to a positive integer representing the timeout in milliseconds for pending segments. For example:

*   json
*   yaml
*   toml

    {  "streaming": 100}

    streaming: 100

    streaming = 100

warning

Setting a very low timeout (e.g., 0 or 50ms) may cause visual glitches depending on the shell's rendering capabilities. We recommend starting with a timeout of around 100ms and adjusting based on your experience.

Shell Support[​](https://ohmyposh.dev/docs/experimental/streaming#shell-support "Direct link to Shell Support")

----------------------------------------------------------------------------------------------------------------

Streaming mode is currently supported in:

*   **PowerShell** (version 7.2+)
*   **Zsh**
*   **Fish**

Support for additional shells may be added in future releases.

Feedback[​](https://ohmyposh.dev/docs/experimental/streaming#feedback "Direct link to Feedback")

-------------------------------------------------------------------------------------------------

If you encounter issues or have suggestions for the streaming feature, please open an issue on the [Oh My Posh GitHub repository](https://github.com/JanDeDobbeleer/oh-my-posh/issues)
.

*   [What is Streaming?](https://ohmyposh.dev/docs/experimental/streaming#what-is-streaming)
    
*   [How Does It Work?](https://ohmyposh.dev/docs/experimental/streaming#how-does-it-work)
    
*   [Enabling Streaming](https://ohmyposh.dev/docs/experimental/streaming#enabling-streaming)
    
*   [Shell Support](https://ohmyposh.dev/docs/experimental/streaming#shell-support)
    
*   [Feedback](https://ohmyposh.dev/docs/experimental/streaming#feedback)