'use client';

import React from 'react';
import { useRouter } from 'next/navigation';

interface AnchorHeadingProps {
  level: 1 | 2 | 3 | 4 | 5 | 6;
  children: React.ReactNode;
  className?: string;
  id?: string;
}

const AnchorHeading: React.FC<AnchorHeadingProps> = ({ 
  level, 
  children, 
  className = '',
  id
}) => {
  const router = useRouter();
  
  // Generate an ID from the children if none is provided
  const headingId = id || (typeof children === 'string' 
    ? children.toLowerCase().replace(/\s+/g, '-').replace(/[^\w-]/g, '') 
    : '');
  
  const handleAnchorClick = (e: React.MouseEvent) => {
    e.preventDefault();
    const hash = `#${headingId}`;
    router.push(hash);
    
    // Update URL without page reload
    window.history.pushState(null, '', hash);
  };

  const HeadingTag = `h${level}` as keyof JSX.IntrinsicElements;
  
  return (
    <HeadingTag id={headingId} className={`group relative ${className}`}>
      {children}
      <a
        href={`#${headingId}`}
        onClick={handleAnchorClick}
        className="ml-2 opacity-0 group-hover:opacity-100 transition-opacity text-nix-primary hover:text-nix-dark"
        aria-label={`Link to ${typeof children === 'string' ? children : 'this heading'}`}
      >
        #
      </a>
    </HeadingTag>
  );
};

export default AnchorHeading;
