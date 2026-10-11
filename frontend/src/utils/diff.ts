export interface DiffPart {
  type: 'added' | 'removed' | 'same';
  text: string;
}

/**
 * Computes word-level diff between reference (original) text and distorted (perturbed) text.
 */
export function computeWordDiff(original: string, perturbed: string): DiffPart[] {
  if (!original && !perturbed) return [];
  if (!original) return [{ type: 'added', text: perturbed }];
  if (!perturbed) return [{ type: 'removed', text: original }];
  if (original === perturbed) return [{ type: 'same', text: original }];

  // Simple token matching diff algorithm
  const origTokens = original.split(/(\s+)/);
  const pertTokens = perturbed.split(/(\s+)/);

  const result: DiffPart[] = [];
  let i = 0;
  let j = 0;

  while (i < origTokens.length || j < pertTokens.length) {
    if (i < origTokens.length && j < pertTokens.length && origTokens[i] === pertTokens[j]) {
      result.push({ type: 'same', text: origTokens[i] });
      i++;
      j++;
    } else {
      // Look ahead for matching token
      let matchI = -1;
      let matchJ = -1;
      const windowSize = 7;

      for (let lookI = i; lookI < Math.min(i + windowSize, origTokens.length); lookI++) {
        for (let lookJ = j; lookJ < Math.min(j + windowSize, pertTokens.length); lookJ++) {
          if (origTokens[lookI] === pertTokens[lookJ] && origTokens[lookI].trim().length > 0) {
            matchI = lookI;
            matchJ = lookJ;
            break;
          }
        }
        if (matchI !== -1) break;
      }

      if (matchI !== -1 && matchJ !== -1) {
        while (i < matchI) {
          result.push({ type: 'removed', text: origTokens[i] });
          i++;
        }
        while (j < matchJ) {
          result.push({ type: 'added', text: pertTokens[j] });
          j++;
        }
      } else {
        if (i < origTokens.length) {
          result.push({ type: 'removed', text: origTokens[i] });
          i++;
        }
        if (j < pertTokens.length) {
          result.push({ type: 'added', text: pertTokens[j] });
          j++;
        }
      }
    }
  }

  return result;
}
