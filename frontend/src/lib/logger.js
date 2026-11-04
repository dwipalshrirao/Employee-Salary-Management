function normalizeError(error) {
  if (error instanceof Error) {
    return {
      name: error.name,
      message: error.message,
      stack: error.stack,
    };
  }

  const message = typeof error === "string" ? error : String(error);
  return {
    name: "Error",
    message,
    stack: new Error(message).stack,
  };
}

export function logUnexpectedError(source, error, extra = {}) {
  console.error("unexpected_frontend_error", {
    source,
    ...normalizeError(error),
    ...extra,
  });
}

export function installGlobalErrorLogging(target = window) {
  const onError = (event) => {
    logUnexpectedError(
      "window.error",
      event.error ?? new Error(event.message || "Unknown window error"),
      {
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
      },
    );
  };
  const onUnhandledRejection = (event) => {
    logUnexpectedError(
      "unhandledrejection",
      event.reason ?? new Error("Unhandled promise rejection"),
    );
  };

  target.addEventListener("error", onError);
  target.addEventListener("unhandledrejection", onUnhandledRejection);

  return () => {
    target.removeEventListener("error", onError);
    target.removeEventListener("unhandledrejection", onUnhandledRejection);
  };
}
