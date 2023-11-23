export const GlobalStyles = () => {
  return (
    <style jsx global>{`
      *,
      *::before,
      *::after {
        box-sizing: border-box;
      }

      :root {
        --bg: #fff;
        --border: #c8d1dc;
        --text: #121a24;
        --highlight: #1bebb9;
        --highlight50: #d1fbf1;

        height: 100%;
        margin: 0;
        padding: 0;
        width: 100%;
      }

      body {
        background: var(--bg);
        color: var(--text);
        font-family:
          -apple-system,
          BlinkMacSystemFont,
          Segoe UI,
          Roboto,
          Oxygen,
          Ubuntu,
          Cantarell,
          Fira Sans,
          Droid Sans,
          Helvetica Neue,
          sans-serif;
        font-size: 14px;
        height: 100%;
        width: 100%;
        margin: 0;
        padding: 0;
      }

      #__next {
        height: 100%;
      }

      button {
        align-items: center;
        background: var(--highlight);
        border: none;
        border-radius: 4px;
        color: var(--text);
        cursor: pointer;
        display: flex;
        gap: 4px;
        font-weight: 600;
        outline: 0 solid var(--highlight50);
        padding: 6px 8px;
      }
      button:not([disabled]):hover,
      button:not([disabled]):focus-visible {
        outline-width: 2px;
      }
      button[disabled] {
        cursor: default;
        opacity: 0.5;
      }

      input {
        background: var(--bg);
        border: 1px solid var(--border);
        border-radius: 4px;
        color: var(--text);
        outline: 0 solid var(--highlight50);
        padding: 6px 8px;
      }
      input:focus-visible {
        outline-width: 2px;
      }
    `}</style>
  );
};
