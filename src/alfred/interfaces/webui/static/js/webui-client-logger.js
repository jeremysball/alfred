(() => {
  const PREFIX = '[webui-client]';
  const MARKER = '__ALFRED_WEBUI_CLIENT_LOGGER__';

  if (window[MARKER]) {
    return;
  }

  const methodNames = ['log', 'info', 'warn', 'error', 'debug'];
  const originals = {};

  for (const methodName of methodNames) {
    originals[methodName] = console[methodName].bind(console);
  }

  const formatArgs = (args) => {
    if (args.length === 0) {
      return [PREFIX];
    }

    const [first, ...rest] = args;
    if (typeof first === 'string') {
      return [`${PREFIX} ${first}`, ...rest];
    }

    return [PREFIX, ...args];
  };

  for (const methodName of methodNames) {
    console[methodName] = (...args) => {
      originals[methodName](...formatArgs(args));
    };
  }

  window[MARKER] = true;
})();
