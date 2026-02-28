import { cn } from '../../lib/utils';

interface MarkdownProps {
  content: string;
  className?: string;
}

/**
 * Lightweight markdown renderer for agent responses.
 * Handles: headers, bold, italic, links, lists, code blocks, inline code, hr.
 */
export function Markdown({ content, className }: MarkdownProps) {
  const lines = content.split('\n');
  const elements: JSX.Element[] = [];
  let key = 0;
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Code block
    if (line.trimStart().startsWith('```')) {
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trimStart().startsWith('```')) {
        codeLines.push(lines[i]);
        i++;
      }
      i++; // skip closing ```
      elements.push(
        <pre
          key={key++}
          className="my-2 overflow-x-auto rounded-md bg-zinc-950 border border-zinc-700 p-3 text-xs leading-relaxed"
        >
          <code className="text-green-300">{codeLines.join('\n')}</code>
        </pre>
      );
      continue;
    }

    // Horizontal rule
    if (/^---+$/.test(line.trim()) || /^\*\*\*+$/.test(line.trim())) {
      elements.push(<hr key={key++} className="my-3 border-zinc-700" />);
      i++;
      continue;
    }

    // Empty line
    if (line.trim() === '') {
      i++;
      continue;
    }

    // Headers
    const headerMatch = line.match(/^(#{1,4})\s+(.+)$/);
    if (headerMatch) {
      const level = headerMatch[1].length;
      const text = headerMatch[2];
      const Tag = `h${level}` as keyof JSX.IntrinsicElements;
      const sizes: Record<number, string> = {
        1: 'text-lg font-bold text-zinc-100 mt-4 mb-2',
        2: 'text-base font-semibold text-zinc-200 mt-3 mb-1.5',
        3: 'text-sm font-semibold text-zinc-300 mt-2 mb-1',
        4: 'text-sm font-medium text-zinc-400 mt-2 mb-1',
      };
      elements.push(
        <Tag key={key++} className={sizes[level]}>
          {renderInline(text)}
        </Tag>
      );
      i++;
      continue;
    }

    // Unordered list
    if (/^\s*[-*+]\s+/.test(line)) {
      const listItems: { indent: number; text: string }[] = [];
      while (i < lines.length && /^\s*[-*+]\s+/.test(lines[i])) {
        const match = lines[i].match(/^(\s*)[-*+]\s+(.+)$/);
        if (match) {
          listItems.push({ indent: match[1].length, text: match[2] });
        }
        i++;
      }
      elements.push(
        <ul key={key++} className="my-1.5 space-y-0.5 pl-4">
          {listItems.map((item, idx) => (
            <li
              key={idx}
              className="text-sm text-zinc-300 list-disc"
              style={{ marginLeft: Math.min(item.indent, 8) * 4 }}
            >
              {renderInline(item.text)}
            </li>
          ))}
        </ul>
      );
      continue;
    }

    // Ordered list
    if (/^\s*\d+[.)]\s+/.test(line)) {
      const listItems: string[] = [];
      while (i < lines.length && /^\s*\d+[.)]\s+/.test(lines[i])) {
        const match = lines[i].match(/^\s*\d+[.)]\s+(.+)$/);
        if (match) listItems.push(match[1]);
        i++;
      }
      elements.push(
        <ol key={key++} className="my-1.5 space-y-0.5 pl-4">
          {listItems.map((text, idx) => (
            <li key={idx} className="text-sm text-zinc-300 list-decimal">
              {renderInline(text)}
            </li>
          ))}
        </ol>
      );
      continue;
    }

    // Regular paragraph
    elements.push(
      <p key={key++} className="text-sm text-zinc-300 leading-relaxed my-1">
        {renderInline(line)}
      </p>
    );
    i++;
  }

  return <div className={cn('space-y-0', className)}>{elements}</div>;
}

/** Render inline markdown: bold, italic, code, links */
function renderInline(text: string): (string | JSX.Element)[] {
  const parts: (string | JSX.Element)[] = [];
  // Pattern matches: **bold**, *italic*, `code`, [text](url)
  const pattern = /(\*\*(.+?)\*\*)|(\*(.+?)\*)|(`(.+?)`)|(\[(.+?)\]\((.+?)\))/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let partKey = 0;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }

    if (match[1]) {
      // **bold**
      parts.push(
        <strong key={partKey++} className="font-semibold text-zinc-100">
          {match[2]}
        </strong>
      );
    } else if (match[3]) {
      // *italic*
      parts.push(
        <em key={partKey++} className="italic text-zinc-200">
          {match[4]}
        </em>
      );
    } else if (match[5]) {
      // `code`
      parts.push(
        <code
          key={partKey++}
          className="px-1 py-0.5 rounded bg-zinc-800 text-green-300 text-xs font-mono"
        >
          {match[6]}
        </code>
      );
    } else if (match[7]) {
      // [text](url)
      parts.push(
        <a
          key={partKey++}
          href={match[9]}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-400 hover:text-blue-300 underline underline-offset-2"
        >
          {match[8]}
        </a>
      );
    }

    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts;
}
