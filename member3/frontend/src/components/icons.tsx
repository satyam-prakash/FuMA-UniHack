/**
 * Icons as inline SVG.
 *
 * Two reasons this is not `lucide-react`:
 *  1. Design: DESIGN.md requires square terminals and sharp joins ("look like
 *     technical drawings"). Lucide ships `stroke-linecap="round"` on every path,
 *     so every icon would have had to be overridden anyway.
 *  2. Build: the package resolves to ~1700 separate modules, which stalls the
 *     Vite transform step for minutes on this machine.
 *
 * Stroke weight stays in the 1.5-2px band the design system specifies.
 */

import type { SVGProps } from 'react';

interface IconProps extends Omit<SVGProps<SVGSVGElement>, 'children'> {
  size?: number;
  strokeWidth?: number;
}

function Icon({ size = 20, strokeWidth = 1.75, children, ...rest }: IconProps & { children: React.ReactNode }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      // Square terminals + miter joins: the technical-drawing rule.
      strokeLinecap="square"
      strokeLinejoin="miter"
      aria-hidden="true"
      {...rest}
    >
      {children}
    </svg>
  );
}

export const Upload = (props: IconProps) => (
  <Icon {...props}>
    <path d="M4 16v3h16v-3" />
    <path d="M12 16V4" />
    <path d="M7 9l5-5 5 5" />
  </Icon>
);

export const UploadCloud = (props: IconProps) => (
  <Icon {...props}>
    <path d="M4 15a4 4 0 014-4 5 5 0 019.6-1.3A4 4 0 0120 15" />
    <path d="M12 20v-8" />
    <path d="M8.5 15.5L12 12l3.5 3.5" />
  </Icon>
);

export const ListChecks = (props: IconProps) => (
  <Icon {...props}>
    <path d="M3 5h3v3H3z" />
    <path d="M3 16h3v3H3z" />
    <path d="M10 6.5h11" />
    <path d="M10 17.5h11" />
  </Icon>
);

export const LayoutDashboard = (props: IconProps) => (
  <Icon {...props}>
    <path d="M3 3h7v7H3z" />
    <path d="M14 3h7v4h-7z" />
    <path d="M14 11h7v10h-7z" />
    <path d="M3 14h7v7H3z" />
  </Icon>
);

export const ClipboardCheck = (props: IconProps) => (
  <Icon {...props}>
    <path d="M9 3h6v3H9z" />
    <path d="M5 6h4M15 6h4v15H5V6" />
    <path d="M8.5 13l2.5 2.5L16 11" />
  </Icon>
);

export const Download = (props: IconProps) => (
  <Icon {...props}>
    <path d="M4 16v3h16v-3" />
    <path d="M12 4v11" />
    <path d="M7 10l5 5 5-5" />
  </Icon>
);

export const Search = (props: IconProps) => (
  <Icon {...props}>
    <circle cx="11" cy="11" r="6" />
    <path d="M16 16l4.5 4.5" />
  </Icon>
);

export const Check = (props: IconProps) => (
  <Icon {...props}>
    <path d="M4 12.5l5 5L20 6.5" />
  </Icon>
);

export const AlertTriangle = (props: IconProps) => (
  <Icon {...props}>
    <path d="M12 3L22 20H2L12 3z" />
    <path d="M12 9v5" />
    <path d="M12 17h.01" />
  </Icon>
);

export const FileSpreadsheet = (props: IconProps) => (
  <Icon {...props}>
    <path d="M5 2h9l5 5v15H5z" />
    <path d="M14 2v5h5" />
    <path d="M8 12h8M8 16h8" />
    <path d="M12 12v8" />
  </Icon>
);

export const FileText = (props: IconProps) => (
  <Icon {...props}>
    <path d="M5 2h9l5 5v15H5z" />
    <path d="M14 2v5h5" />
    <path d="M8 12h7M8 16h7M8 8h3" />
  </Icon>
);

export const ChevronLeft = (props: IconProps) => (
  <Icon {...props}>
    <path d="M14.5 5L8 12l6.5 7" />
  </Icon>
);

export const ChevronRight = (props: IconProps) => (
  <Icon {...props}>
    <path d="M9.5 5L16 12l-6.5 7" />
  </Icon>
);

export const ChevronDown = (props: IconProps) => (
  <Icon {...props}>
    <path d="M5 9.5L12 16l7-6.5" />
  </Icon>
);

export const ArrowLeft = (props: IconProps) => (
  <Icon {...props}>
    <path d="M20 12H4" />
    <path d="M10 6L4 12l6 6" />
  </Icon>
);
