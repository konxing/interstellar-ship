/** Monotonic token so a superseded glTF callback can recognise it lost the race. */
export function createLoadGuard() {
  let latest = 0;
  return {
    begin() {
      latest += 1;
      return latest;
    },
    isCurrent(token) {
      return token === latest;
    },
  };
}
