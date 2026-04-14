/**
 * PURPOSE: PostCSS config: Tailwind CSS v4. Never change (per spec).
 *
 * OWNS:
 *   - PostCSS plugin pipeline (Tailwind v4 via @tailwindcss/postcss)
 *
 * TOUCH POINTS:
 *   - app/global.css is processed by this pipeline
 */

export default {
  plugins: {
    '@tailwindcss/postcss': {},
  },
};
