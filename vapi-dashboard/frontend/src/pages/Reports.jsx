import { useState, useEffect, useMemo, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { getReports, getReport } from '../services/api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
// Lazy load heavy libraries
const loadPdfLibs = () => Promise.all([
  import('jspdf'),
  import('html2canvas')
]);
const loadWordLibs = () => Promise.all([
  import('docx'),
  import('file-saver')
]);
import {
  ChevronLeft,
  Download,
  Calendar,
  Phone,
  DollarSign,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  FileText,
  ChevronDown,
  ChevronRight,
  FileDown,
  Loader2
} from 'lucide-react';

// Custom components for ReactMarkdown
const MarkdownComponents = {
  // Hide raw anchor tags
  a: ({ node, children, href, ...props }) => {
    // If it's an anchor with just an id (like <a id="..."></a>), hide it
    if (!children || (Array.isArray(children) && children.length === 0)) {
      return null;
    }
    return (
      <a href={href} className="text-primary-600 hover:text-primary-800 underline" {...props}>
        {children}
      </a>
    );
  },

  // Better heading styles with IDs for navigation
  h1: ({ children }) => {
    const text = typeof children === 'string' ? children :
      (Array.isArray(children) ? children.join('') : String(children));
    const id = text.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
    return (
      <h1 id={id} className="text-2xl font-bold text-gray-900 mt-8 mb-4 pb-2 border-b-2 border-primary-500 scroll-mt-4">
        {children}
      </h1>
    );
  },
  h2: ({ children }) => {
    const text = typeof children === 'string' ? children :
      (Array.isArray(children) ? children.join('') : String(children));
    const id = text.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
    return (
      <h2 id={id} className="text-xl font-semibold text-gray-800 mt-6 mb-3 pb-1 border-b border-gray-200 scroll-mt-4">
        {children}
      </h2>
    );
  },
  h3: ({ children }) => {
    const text = typeof children === 'string' ? children :
      (Array.isArray(children) ? children.join('') : String(children));
    const id = text.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
    return (
      <h3 id={id} className="text-lg font-medium text-gray-700 mt-4 mb-2 scroll-mt-4">
        {children}
      </h3>
    );
  },

  // Better table styles
  table: ({ children }) => (
    <div className="overflow-x-auto my-4">
      <table className="min-w-full divide-y divide-gray-200 border border-gray-200 rounded-lg overflow-hidden">
        {children}
      </table>
    </div>
  ),
  thead: ({ children }) => (
    <thead className="bg-gray-50">{children}</thead>
  ),
  th: ({ children }) => (
    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider border-b">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="px-4 py-3 text-sm text-gray-700 border-b border-gray-100">
      {children}
    </td>
  ),
  tr: ({ children }) => (
    <tr className="hover:bg-gray-50 transition-colors">{children}</tr>
  ),

  // Better list styles
  ul: ({ children }) => (
    <ul className="list-disc list-inside space-y-1 my-2 text-gray-700">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="list-decimal list-inside space-y-1 my-2 text-gray-700">{children}</ol>
  ),

  // Better blockquote (for summaries)
  blockquote: ({ children }) => (
    <blockquote className="border-l-4 border-primary-400 bg-primary-50 pl-4 py-2 my-3 italic text-gray-700 rounded-r">
      {children}
    </blockquote>
  ),

  // Code blocks
  code: ({ inline, children, ...props }) => {
    if (inline) {
      return (
        <code className="bg-gray-100 px-1.5 py-0.5 rounded text-sm font-mono text-gray-800" {...props}>
          {children}
        </code>
      );
    }
    return (
      <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto my-3 text-sm">
        <code {...props}>{children}</code>
      </pre>
    );
  },
  pre: ({ children }) => <>{children}</>,

  // Strong/bold
  strong: ({ children }) => (
    <strong className="font-semibold text-gray-900">{children}</strong>
  ),

  // Paragraphs
  p: ({ children }) => (
    <p className="my-2 text-gray-700 leading-relaxed">{children}</p>
  ),

  // Horizontal rule
  hr: () => <hr className="my-6 border-gray-300" />,
};

// Extract sections from markdown for navigation
function extractSections(markdown) {
  const sections = [];
  const lines = markdown.split('\n');

  for (const line of lines) {
    if (line.startsWith('## ')) {
      const title = line.replace('## ', '').trim();
      const id = title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
      sections.push({ title, id, level: 2 });
    }
  }

  return sections;
}

// Parse markdown to extract structured data for Word export
function parseMarkdownForWord(markdown) {
  const elements = [];
  const lines = markdown.split('\n');
  let inCodeBlock = false;
  let inTable = false;
  let tableRows = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Skip anchor tags
    if (line.includes('<a id="') || line.trim() === '') continue;

    // Code blocks
    if (line.startsWith('```')) {
      inCodeBlock = !inCodeBlock;
      continue;
    }

    if (inCodeBlock) {
      elements.push({ type: 'code', text: line });
      continue;
    }

    // Tables
    if (line.startsWith('|')) {
      if (!inTable) {
        inTable = true;
        tableRows = [];
      }
      // Skip separator rows
      if (!line.includes('---')) {
        const cells = line.split('|').filter(c => c.trim()).map(c => c.trim());
        if (cells.length > 0) {
          tableRows.push(cells);
        }
      }
      continue;
    } else if (inTable) {
      inTable = false;
      if (tableRows.length > 0) {
        elements.push({ type: 'table', rows: tableRows });
        tableRows = [];
      }
    }

    // Headings
    if (line.startsWith('# ')) {
      elements.push({ type: 'h1', text: line.replace('# ', '') });
    } else if (line.startsWith('## ')) {
      elements.push({ type: 'h2', text: line.replace('## ', '') });
    } else if (line.startsWith('### ')) {
      elements.push({ type: 'h3', text: line.replace('### ', '') });
    } else if (line.startsWith('> ')) {
      elements.push({ type: 'quote', text: line.replace('> ', '') });
    } else if (line.startsWith('- ')) {
      elements.push({ type: 'bullet', text: line.replace('- ', '') });
    } else if (line.match(/^\d+\. /)) {
      elements.push({ type: 'numbered', text: line.replace(/^\d+\. /, '') });
    } else if (line.trim()) {
      elements.push({ type: 'paragraph', text: line });
    }
  }

  // Handle remaining table
  if (tableRows.length > 0) {
    elements.push({ type: 'table', rows: tableRows });
  }

  return elements;
}

// Generate Word document from parsed markdown
async function generateWordDocument(report, reportDate, libs) {
  const { Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType, saveAs } = libs;
  const elements = parseMarkdownForWord(report.markdown || '');
  const children = [];

  for (const el of elements) {
    switch (el.type) {
      case 'h1':
        children.push(new Paragraph({
          text: el.text,
          heading: HeadingLevel.HEADING_1,
          spacing: { before: 400, after: 200 },
        }));
        break;
      case 'h2':
        children.push(new Paragraph({
          text: el.text,
          heading: HeadingLevel.HEADING_2,
          spacing: { before: 300, after: 150 },
        }));
        break;
      case 'h3':
        children.push(new Paragraph({
          text: el.text,
          heading: HeadingLevel.HEADING_3,
          spacing: { before: 200, after: 100 },
        }));
        break;
      case 'paragraph':
        children.push(new Paragraph({
          children: parseTextWithBold(el.text, TextRun),
          spacing: { after: 100 },
        }));
        break;
      case 'quote':
        children.push(new Paragraph({
          children: [new TextRun({ text: el.text, italics: true })],
          indent: { left: 720 },
          spacing: { after: 100 },
        }));
        break;
      case 'bullet':
        children.push(new Paragraph({
          children: parseTextWithBold(el.text, TextRun),
          bullet: { level: 0 },
          spacing: { after: 50 },
        }));
        break;
      case 'numbered':
        children.push(new Paragraph({
          children: parseTextWithBold(el.text, TextRun),
          numbering: { reference: 'default-numbering', level: 0 },
          spacing: { after: 50 },
        }));
        break;
      case 'code':
        children.push(new Paragraph({
          children: [new TextRun({ text: el.text, font: 'Courier New', size: 20 })],
          spacing: { after: 50 },
        }));
        break;
      case 'table':
        if (el.rows.length > 0) {
          const tableRows = el.rows.map((row, rowIndex) =>
            new TableRow({
              children: row.map(cell =>
                new TableCell({
                  children: [new Paragraph({
                    children: parseTextWithBold(cell, TextRun),
                    spacing: { after: 0 },
                  })],
                  width: { size: 100 / row.length, type: WidthType.PERCENTAGE },
                  shading: rowIndex === 0 ? { fill: 'E5E7EB' } : undefined,
                })
              ),
            })
          );
          children.push(new Table({
            rows: tableRows,
            width: { size: 100, type: WidthType.PERCENTAGE },
          }));
          children.push(new Paragraph({ text: '', spacing: { after: 200 } }));
        }
        break;
    }
  }

  const doc = new Document({
    sections: [{
      properties: {},
      children: children,
    }],
    numbering: {
      config: [{
        reference: 'default-numbering',
        levels: [{
          level: 0,
          format: 'decimal',
          text: '%1.',
          alignment: 'start',
        }],
      }],
    },
  });

  const blob = await Packer.toBlob(doc);
  saveAs(blob, `vapi-report-${reportDate}.docx`);
}

// Parse text with **bold** markers
function parseTextWithBold(text, TextRun) {
  const parts = [];
  const regex = /\*\*([^*]+)\*\*/g;
  let lastIndex = 0;
  let match;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(new TextRun({ text: text.slice(lastIndex, match.index) }));
    }
    parts.push(new TextRun({ text: match[1], bold: true }));
    lastIndex = regex.lastIndex;
  }

  if (lastIndex < text.length) {
    parts.push(new TextRun({ text: text.slice(lastIndex) }));
  }

  return parts.length > 0 ? parts : [new TextRun({ text })];
}

// Report Detail View Component
function ReportDetail({ report, onBack }) {
  const [activeSection, setActiveSection] = useState('');
  const [downloading, setDownloading] = useState(null);
  const contentRef = useRef(null);

  const sections = useMemo(() => extractSections(report.markdown || ''), [report.markdown]);

  // Clean markdown - remove standalone anchor tags
  const cleanMarkdown = useMemo(() => {
    return (report.markdown || '')
      .replace(/<a id="[^"]*"><\/a>\n*/g, '')
      .replace(/<a id="[^"]*"><\/a>/g, '');
  }, [report.markdown]);

  const scrollToSection = (id) => {
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
      setActiveSection(id);
    }
  };

  // Extract key metrics for the header
  const metrics = report.metrics || {};

  // Get report date for filename
  const reportDate = new Date(report.generated_at).toISOString().split('T')[0];

  // Download as PDF - text-based approach
  const downloadPDF = async () => {
    setDownloading('pdf');
    try {
      // Lazy load jsPDF
      const [{ jsPDF }] = await loadPdfLibs();
      const pdf = new jsPDF({
        orientation: 'portrait',
        unit: 'mm',
        format: 'a4',
      });

      const pageWidth = pdf.internal.pageSize.getWidth();
      const pageHeight = pdf.internal.pageSize.getHeight();
      const margin = 15;
      const contentWidth = pageWidth - (margin * 2);
      let y = margin;

      const checkPageBreak = (neededHeight) => {
        if (y + neededHeight > pageHeight - margin) {
          pdf.addPage();
          y = margin;
          return true;
        }
        return false;
      };

      const addText = (text, options = {}) => {
        const { fontSize = 10, fontStyle = 'normal', color = [0, 0, 0], indent = 0 } = options;
        pdf.setFontSize(fontSize);
        pdf.setFont('helvetica', fontStyle);
        pdf.setTextColor(...color);

        const lines = pdf.splitTextToSize(text, contentWidth - indent);
        const lineHeight = fontSize * 0.4;

        checkPageBreak(lines.length * lineHeight);

        lines.forEach(line => {
          if (checkPageBreak(lineHeight)) {}
          pdf.text(line, margin + indent, y);
          y += lineHeight;
        });
        y += 2;
      };

      const addTable = (rows) => {
        if (rows.length === 0) return;

        const colCount = rows[0].length;
        const colWidth = contentWidth / colCount;
        const cellPadding = 2;
        const rowHeight = 7;

        rows.forEach((row, rowIndex) => {
          checkPageBreak(rowHeight + 2);

          // Background for header
          if (rowIndex === 0) {
            pdf.setFillColor(240, 240, 240);
            pdf.rect(margin, y - 1, contentWidth, rowHeight, 'F');
          }

          // Draw cells
          row.forEach((cell, colIndex) => {
            const x = margin + (colIndex * colWidth);
            pdf.setFontSize(8);
            pdf.setFont('helvetica', rowIndex === 0 ? 'bold' : 'normal');
            pdf.setTextColor(0, 0, 0);

            // Truncate long text
            let cellText = String(cell || '');
            const maxWidth = colWidth - (cellPadding * 2);
            while (pdf.getTextWidth(cellText) > maxWidth && cellText.length > 3) {
              cellText = cellText.slice(0, -4) + '...';
            }

            pdf.text(cellText, x + cellPadding, y + 4);
          });

          // Draw row border
          pdf.setDrawColor(200, 200, 200);
          pdf.line(margin, y + rowHeight - 1, margin + contentWidth, y + rowHeight - 1);

          y += rowHeight;
        });
        y += 3;
      };

      // Parse and render markdown
      const elements = parseMarkdownForWord(cleanMarkdown);

      // Title
      pdf.setFontSize(18);
      pdf.setFont('helvetica', 'bold');
      pdf.setTextColor(30, 64, 175);
      pdf.text('VAPI Call Analysis Report', margin, y);
      y += 10;

      // Report info
      pdf.setFontSize(10);
      pdf.setFont('helvetica', 'normal');
      pdf.setTextColor(100, 100, 100);
      pdf.text(`Generated: ${new Date(report.generated_at).toLocaleString()}`, margin, y);
      y += 5;
      pdf.text(`Date: ${reportDate}`, margin, y);
      y += 8;

      // Metrics summary box
      const metricsY = y;
      pdf.setFillColor(249, 250, 251);
      pdf.rect(margin, y, contentWidth, 20, 'F');
      pdf.setDrawColor(229, 231, 235);
      pdf.rect(margin, y, contentWidth, 20, 'S');

      const metricBoxWidth = contentWidth / 4;
      const metricLabels = ['Total Calls', 'Success Rate', 'Total Cost', 'Avg Duration'];
      const metricValues = [
        String(metrics.total_calls || 0),
        `${metrics.success_rate || 0}%`,
        `$${(metrics.total_cost || 0).toFixed(2)}`,
        metrics.avg_duration_formatted || '0:00'
      ];

      metricLabels.forEach((label, i) => {
        const x = margin + (i * metricBoxWidth) + 5;
        pdf.setFontSize(8);
        pdf.setTextColor(100, 100, 100);
        pdf.text(label, x, y + 7);
        pdf.setFontSize(14);
        pdf.setFont('helvetica', 'bold');
        pdf.setTextColor(30, 30, 30);
        pdf.text(metricValues[i], x, y + 15);
      });

      y += 28;
      pdf.setFont('helvetica', 'normal');

      // Render content
      for (const el of elements) {
        switch (el.type) {
          case 'h1':
            y += 4;
            checkPageBreak(12);
            addText(el.text, { fontSize: 16, fontStyle: 'bold', color: [30, 64, 175] });
            pdf.setDrawColor(30, 64, 175);
            pdf.line(margin, y - 1, margin + contentWidth, y - 1);
            y += 2;
            break;
          case 'h2':
            y += 3;
            checkPageBreak(10);
            addText(el.text, { fontSize: 13, fontStyle: 'bold', color: [55, 65, 81] });
            pdf.setDrawColor(229, 231, 235);
            pdf.line(margin, y - 1, margin + contentWidth, y - 1);
            y += 1;
            break;
          case 'h3':
            y += 2;
            checkPageBreak(8);
            addText(el.text, { fontSize: 11, fontStyle: 'bold', color: [75, 85, 99] });
            break;
          case 'paragraph':
            addText(el.text.replace(/\*\*/g, ''), { fontSize: 9 });
            break;
          case 'quote':
            addText(el.text, { fontSize: 9, fontStyle: 'italic', color: [107, 114, 128], indent: 5 });
            break;
          case 'bullet':
            addText(`• ${el.text.replace(/\*\*/g, '')}`, { fontSize: 9, indent: 3 });
            break;
          case 'table':
            addTable(el.rows);
            break;
          case 'code':
            pdf.setFillColor(243, 244, 246);
            checkPageBreak(6);
            pdf.rect(margin, y - 1, contentWidth, 5, 'F');
            addText(el.text, { fontSize: 8, indent: 2 });
            break;
        }
      }

      // Footer on each page
      const totalPages = pdf.internal.getNumberOfPages();
      for (let i = 1; i <= totalPages; i++) {
        pdf.setPage(i);
        pdf.setFontSize(8);
        pdf.setTextColor(150, 150, 150);
        pdf.text(`Page ${i} of ${totalPages}`, pageWidth - margin - 20, pageHeight - 8);
        pdf.text('VAPI Dashboard Report', margin, pageHeight - 8);
      }

      pdf.save(`vapi-report-${reportDate}.pdf`);
    } catch (error) {
      console.error('PDF generation error:', error);
      alert('Failed to generate PDF. Please try again.');
    } finally {
      setDownloading(null);
    }
  };

  // Download as Word
  const downloadWord = async () => {
    setDownloading('word');
    try {
      // Lazy load docx and file-saver
      const [docxModule, fileSaverModule] = await loadWordLibs();
      const { Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType } = docxModule;
      const { saveAs } = fileSaverModule;

      await generateWordDocument(report, reportDate, { Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType, saveAs });
    } catch (error) {
      console.error('Word generation error:', error);
      alert('Failed to generate Word document. Please try again.');
    } finally {
      setDownloading(null);
    }
  };

  return (
    <div className="flex gap-6">
      {/* Sticky Sidebar - Table of Contents */}
      <div className="hidden lg:block w-64 flex-shrink-0">
        <div className="sticky top-4 bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <h3 className="font-semibold text-gray-900 mb-3 flex items-center">
            <FileText className="w-4 h-4 mr-2" />
            Contents
          </h3>
          <nav className="space-y-1">
            {sections.map((section) => (
              <button
                key={section.id}
                onClick={() => scrollToSection(section.id)}
                className={`block w-full text-left px-2 py-1.5 text-sm rounded transition-colors ${
                  activeSection === section.id
                    ? 'bg-primary-100 text-primary-700 font-medium'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                {section.title}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 min-w-0">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-4">
          <div className="flex items-center justify-between mb-4">
            <button
              onClick={onBack}
              className="flex items-center text-primary-600 hover:text-primary-800 font-medium"
            >
              <ChevronLeft className="w-5 h-5 mr-1" />
              Back to Reports
            </button>
            <div className="flex items-center gap-3">
              {/* Download Buttons */}
              <div className="flex items-center gap-2">
                <button
                  onClick={downloadPDF}
                  disabled={downloading !== null}
                  className="inline-flex items-center px-3 py-1.5 bg-red-50 text-red-700 rounded-lg hover:bg-red-100 transition-colors text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {downloading === 'pdf' ? (
                    <Loader2 className="w-4 h-4 mr-1.5 animate-spin" />
                  ) : (
                    <FileDown className="w-4 h-4 mr-1.5" />
                  )}
                  PDF
                </button>
                <button
                  onClick={downloadWord}
                  disabled={downloading !== null}
                  className="inline-flex items-center px-3 py-1.5 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition-colors text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {downloading === 'word' ? (
                    <Loader2 className="w-4 h-4 mr-1.5 animate-spin" />
                  ) : (
                    <FileDown className="w-4 h-4 mr-1.5" />
                  )}
                  Word
                </button>
              </div>
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <Calendar className="w-4 h-4" />
                {new Date(report.generated_at).toLocaleString()}
              </div>
            </div>
          </div>

          {/* Quick Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-blue-50 rounded-lg p-3">
              <div className="flex items-center text-blue-600 mb-1">
                <Phone className="w-4 h-4 mr-1" />
                <span className="text-xs font-medium">Total Calls</span>
              </div>
              <div className="text-2xl font-bold text-blue-700">{metrics.total_calls || 0}</div>
            </div>
            <div className="bg-green-50 rounded-lg p-3">
              <div className="flex items-center text-green-600 mb-1">
                <CheckCircle className="w-4 h-4 mr-1" />
                <span className="text-xs font-medium">Success Rate</span>
              </div>
              <div className="text-2xl font-bold text-green-700">{metrics.success_rate || 0}%</div>
            </div>
            <div className="bg-purple-50 rounded-lg p-3">
              <div className="flex items-center text-purple-600 mb-1">
                <DollarSign className="w-4 h-4 mr-1" />
                <span className="text-xs font-medium">Total Cost</span>
              </div>
              <div className="text-2xl font-bold text-purple-700">${(metrics.total_cost || 0).toFixed(2)}</div>
            </div>
            <div className="bg-orange-50 rounded-lg p-3">
              <div className="flex items-center text-orange-600 mb-1">
                <Clock className="w-4 h-4 mr-1" />
                <span className="text-xs font-medium">Avg Duration</span>
              </div>
              <div className="text-2xl font-bold text-orange-700">{metrics.avg_duration_formatted || '0:00'}</div>
            </div>
          </div>
        </div>

        {/* Report Content */}
        <div ref={contentRef} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="prose prose-sm max-w-none">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[rehypeRaw]}
              components={MarkdownComponents}
            >
              {cleanMarkdown}
            </ReactMarkdown>
          </div>
        </div>
      </div>
    </div>
  );
}

// Reports List Component
function ReportsList({ reports, onSelectReport }) {
  if (reports.length === 0) {
    return (
      <div className="bg-white shadow rounded-lg p-12 text-center">
        <FileText className="mx-auto h-16 w-16 text-gray-300" />
        <h3 className="mt-4 text-lg font-medium text-gray-900">No reports yet</h3>
        <p className="mt-2 text-gray-500">
          Reports are generated daily at 6:00 AM UTC.<br />
          Select a phone number filter to view reports.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white shadow-sm rounded-lg border border-gray-200 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                Date
              </th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                Calls
              </th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                Success
              </th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                Cost
              </th>
              <th className="px-6 py-3 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">
                Action
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-100">
            {reports.map((report) => {
              const successRate = report.metrics?.success_rate || 0;
              return (
                <tr
                  key={report.date}
                  className="hover:bg-gray-50 cursor-pointer transition-colors"
                  onClick={() => onSelectReport(report.date)}
                >
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <Calendar className="w-4 h-4 text-gray-400 mr-2" />
                      <div>
                        <div className="text-sm font-medium text-gray-900">
                          {new Date(report.date).toLocaleDateString('en-US', {
                            weekday: 'short',
                            month: 'short',
                            day: 'numeric'
                          })}
                        </div>
                        <div className="text-xs text-gray-500">
                          {new Date(report.date).getFullYear()}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <Phone className="w-4 h-4 text-blue-400 mr-2" />
                      <span className="text-sm font-medium text-gray-700">{report.total_calls}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold ${
                      successRate >= 80 ? 'bg-green-100 text-green-800' :
                      successRate >= 60 ? 'bg-yellow-100 text-yellow-800' :
                      'bg-red-100 text-red-800'
                    }`}>
                      {successRate >= 80 ? <CheckCircle className="w-3 h-3 mr-1" /> :
                       successRate >= 60 ? <AlertTriangle className="w-3 h-3 mr-1" /> :
                       <XCircle className="w-3 h-3 mr-1" />}
                      {successRate}%
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <DollarSign className="w-4 h-4 text-purple-400 mr-1" />
                      <span className="text-sm font-medium text-gray-700">
                        {(report.metrics?.total_cost || 0).toFixed(2)}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <button className="inline-flex items-center px-3 py-1.5 bg-primary-50 text-primary-700 rounded-lg hover:bg-primary-100 transition-colors text-sm font-medium">
                      View Report
                      <ChevronRight className="w-4 h-4 ml-1" />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// Main Reports Component
export default function Reports() {
  const [reports, setReports] = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchParams, setSearchParams] = useSearchParams();

  const selectedDate = searchParams.get('date');

  // Fetch reports list
  useEffect(() => {
    async function fetchReports() {
      try {
        setLoading(true);
        const data = await getReports();
        setReports(data.reports || []);
        setError(null);
      } catch (err) {
        setError(err.message || 'Failed to load reports');
      } finally {
        setLoading(false);
      }
    }
    fetchReports();
  }, []);

  // Fetch specific report when date is selected
  useEffect(() => {
    async function fetchReport() {
      if (!selectedDate) {
        setSelectedReport(null);
        return;
      }

      try {
        setLoading(true);
        const data = await getReport(selectedDate);
        setSelectedReport(data.report);
        setError(null);
      } catch (err) {
        setError(err.message || 'Failed to load report');
      } finally {
        setLoading(false);
      }
    }
    fetchReport();
  }, [selectedDate]);

  const handleSelectReport = (date) => {
    setSearchParams({ date });
  };

  const handleBack = () => {
    setSearchParams({});
    setSelectedReport(null);
  };

  if (loading && reports.length === 0 && !selectedReport) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-gray-500">Loading reports...</p>
        </div>
      </div>
    );
  }

  if (error && !selectedReport && reports.length === 0) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-6 py-4 rounded-lg flex items-center">
        <XCircle className="w-5 h-5 mr-2" />
        {error}
      </div>
    );
  }

  // Show report detail view
  if (selectedReport) {
    return <ReportDetail report={selectedReport} onBack={handleBack} />;
  }

  // Show reports list
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Daily Reports</h1>
          <p className="mt-1 text-gray-500">
            Detailed call analysis and cost reports
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm text-gray-500 bg-gray-100 px-3 py-1.5 rounded-lg">
          <Calendar className="w-4 h-4" />
          Last {reports.length} days
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-32">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      ) : (
        <ReportsList reports={reports} onSelectReport={handleSelectReport} />
      )}
    </div>
  );
}
