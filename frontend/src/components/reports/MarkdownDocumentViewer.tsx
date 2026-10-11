import React, { useMemo } from 'react';
import { Marked } from 'marked';

interface MarkdownDocumentViewerProps {
  content: string;
}

export const MarkdownDocumentViewer: React.FC<MarkdownDocumentViewerProps> = ({ content }) => {
  const htmlContent = useMemo(() => {
    if (!content) return '';

    // 1. Preprocess raw content to sanitize paths, links, and development-phase labels
    let preprocessed = content
      // Remove Phase labels from markdown headers
      .replace(/^(#+)\s*Phase\s*\d+\s*[—–-]\s*/gim, '$1 ')
      .replace(/^(#+)\s*Phase\s*\d+:\s*/gim, '$1 ')
      .replace(/^(#+)\s*Phase\s*\d+\s+Final Research Report/gim, '$1 Final Research Report')
      .replace(/^(#+)\s*Phase\s*\d+\s+Controlled Causal Distortion Stress Test Report/gim, '$1 Controlled Distortion Stress Test Report')
      .replace(/^(#+)\s*Phase\s*\d+\s+Research Limitations/gim, '$1 Research Limitations')
      .replace(/^(#+)\s*Phase\s*\d+\s+Baseline Data/gim, '$1 Research Baseline')
      .replace(/^(#+)\s*Phase\s*\d+\s+/gim, '$1 ')
      // Sanitize raw file links [Title](file:///d:/...) -> [Title](artifact:Title)
      .replace(/\[([^\]]+)\]\(file:\/\/\/[^)]+\)/g, (_m, label) => `[${label}](artifact:${label})`)
      // Sanitize raw Windows file links [Title](d:\...)
      .replace(/\[([^\]]+)\]\([a-zA-Z]:\\[^)]+\)/g, (_m, label) => `[${label}](artifact:${label})`)
      // Sanitize inline file:/// paths
      .replace(/file:\/\/\/[a-zA-Z]:[^\s)\]]+/g, (match) => {
        const parts = match.split('/');
        return parts.pop() || match;
      })
      // Sanitize raw Windows absolute paths
      .replace(/[a-zA-Z]:\\(?:[^\s)\]\\]+\\)+([^\s)\]\\]+)/g, '$1');

    const markedInstance = new Marked();

    markedInstance.use({
      renderer: {
        heading({ text, depth }) {
          let cleanHeading = text
            .replace(/Phase\s*\d+\s*[—–-]\s*/gi, '')
            .replace(/Phase\s*\d+:\s*/gi, '')
            .replace(/Phase\s*\d+\s+Final Research Report/gi, 'Final Research Report')
            .replace(/Phase\s*\d+\s+Research Limitations/gi, 'Research Limitations')
            .replace(/Phase\s*\d+/gi, '')
            .trim()
            .replace(/^:\s*/, '')
            .replace(/^[—–-]\s*/, '');

          if (!cleanHeading) cleanHeading = text;

          const depthClasses: Record<number, string> = {
            1: 'text-xl font-bold text-[#0F172A] mt-6 mb-3 pb-2.5 border-b border-[#E2E8F0]',
            2: 'text-base font-bold text-[#064E3B] mt-5 mb-2.5 pt-1 border-b border-[#F1F5F9]',
            3: 'text-sm font-bold text-[#0F172A] mt-4 mb-2',
            4: 'text-xs font-bold text-[#334155] uppercase tracking-wider mt-3 mb-1.5',
            5: 'text-xs font-semibold text-[#475569] mt-2 mb-1',
            6: 'text-xs font-medium text-[#64748B] mt-2 mb-1'
          };

          const cls = depthClasses[depth] || depthClasses[3];
          return `<h${depth} class="${cls}">${cleanHeading}</h${depth}>`;
        },

        link({ href, text }) {
          // Internal local file paths should NOT be rendered as clickable file links or expose developer filesystem
          if (
            !href ||
            href.startsWith('artifact:') ||
            href.startsWith('file:') ||
            href.includes('outputs/') ||
            href.startsWith('/') ||
            href.startsWith('.') ||
            href.endsWith('.json') ||
            href.endsWith('.md')
          ) {
            let cleanText = text
              .replace(/artifact:/g, '')
              .replace(/file:\/\/\/[^\s)]+/g, '')
              .replace(/outputs\/[^\s)]+/g, (m) => m.split('/').pop() || m)
              .replace(/`([^`]+)`/g, '$1')
              .trim();

            if (!cleanText) cleanText = 'Research Artifact';

            return `<span class="inline-flex items-center px-1.5 py-0.5 rounded font-mono text-[11px] bg-slate-100 text-slate-700 border border-slate-200" title="Research artifact reference">${cleanText}</span>`;
          }

          // External web links
          if (href.startsWith('http://') || href.startsWith('https://')) {
            return `<a href="${href}" target="_blank" rel="noopener noreferrer" class="text-emerald-700 hover:text-emerald-800 underline font-medium transition-colors">${text}</a>`;
          }

          return `<span class="font-mono text-xs text-slate-700 bg-slate-100 px-1 py-0.5 rounded">${text}</span>`;
        },

        code({ text, lang }) {
          return `
            <div class="my-3 rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] overflow-hidden">
              ${lang ? `<div class="px-3 py-1 bg-[#F1F5F9] border-b border-[#E2E8F0] text-[10px] font-mono text-[#64748B] uppercase tracking-wider">${lang}</div>` : ''}
              <pre class="p-3.5 text-xs font-mono text-[#0F172A] overflow-x-auto leading-relaxed select-text"><code>${text}</code></pre>
            </div>
          `;
        },

        codespan({ text }) {
          return `<code class="bg-slate-100 text-slate-800 font-mono text-[11px] px-1.5 py-0.5 rounded border border-slate-200 select-text">${text}</code>`;
        },

        hr() {
          return `<hr class="border-t border-[#E2E8F0] my-5" />`;
        }
      }
    });

    try {
      let parsed = markedInstance.parse(preprocessed);
      if (typeof parsed !== 'string') return '';

      // Wrap tables in responsive horizontal scroll wrappers
      parsed = parsed
        .replace(/<table>/g, '<div class="overflow-x-auto my-4 rounded-xl border border-[#E2E8F0] shadow-2xs"><table>')
        .replace(/<\/table>/g, '</table></div>');

      return parsed;
    } catch (err) {
      console.error('Error rendering markdown document:', err);
      return `<pre class="p-4 bg-slate-50 text-xs font-mono whitespace-pre-wrap">${content}</pre>`;
    }
  }, [content]);

  return (
    <article
      className="markdown-document-body text-[#1F2937] max-w-full"
      dangerouslySetInnerHTML={{ __html: htmlContent }}
    />
  );
};
