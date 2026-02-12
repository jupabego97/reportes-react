import { Link } from 'react-router-dom';
import { cn } from '../lib/utils';

interface ProductLinkProps {
  nombre: string;
  className?: string;
  title?: string;
}

export function ProductLink({ nombre, className, title }: ProductLinkProps) {
  const encoded = encodeURIComponent(nombre);
  return (
    <Link
      to={`/producto/${encoded}`}
      className={cn(
        'font-medium hover:underline underline-offset-2 cursor-pointer text-primary',
        className
      )}
      title={title ?? nombre}
    >
      {nombre}
    </Link>
  );
}
