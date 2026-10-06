import type { CSSProperties } from 'react';

/**
 * Shared presentation of the user-supplied dark and light Vigil AI assets.
 */
interface AIOrbProps {
  size?: number;
  variant?: 'default' | 'muted' | 'active';
  animate?: boolean;
  detail?: 'mark' | 'hero';
  className?: string;
  style?: CSSProperties;
}

const SIZES = {
  xs: 16,
  sm: 24,
  md: 48,
  lg: 96,
  xl: 180,
  '2xl': 240,
};

export function AIOrb({
  size = 96,
  variant = 'default',
  animate = true,
  detail = 'mark',
  className = '',
  style,
}: AIOrbProps) {
  const hero = detail === 'hero';
  const opacity = variant === 'muted' ? 0.62 : 1;

  return (
    <span
      aria-hidden="true"
      className={[
        'vigil-ai-symbol',
        hero ? 'vigil-ai-symbol--hero' : 'vigil-ai-symbol--mark',
        variant === 'active' ? 'vigil-ai-symbol--active' : '',
        animate ? 'vigil-ai-symbol--animated' : '',
        className,
      ].filter(Boolean).join(' ')}
      style={{ width: size, height: size, opacity, ...style }}
    >
      <span className="vigil-ai-reference-image" />
    </span>
  );
}

export const OrbXS = (props?: Partial<AIOrbProps>) => <AIOrb size={SIZES.xs} {...props} />;
export const OrbSM = (props?: Partial<AIOrbProps>) => <AIOrb size={SIZES.sm} {...props} />;
export const OrbMD = (props?: Partial<AIOrbProps>) => <AIOrb size={SIZES.md} {...props} />;
export const OrbLG = (props?: Partial<AIOrbProps>) => <AIOrb size={SIZES.lg} {...props} />;
export const OrbXL = (props?: Partial<AIOrbProps>) => <AIOrb size={SIZES.xl} {...props} />;
export const Orb2XL = (props?: Partial<AIOrbProps>) => <AIOrb size={SIZES['2xl']} {...props} />;

export default AIOrb;
