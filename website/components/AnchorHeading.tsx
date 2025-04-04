'use client';

import React, { useEffect } from 'react';

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
  
  // Generate an ID from the children if none is provided
  const headingId = id || (typeof children === 'string' 
    ? children.toLowerCase().replace(/\s+/g, '-').replace(/[^\w-]/g, '') 
    : `heading-${Math.random().toString(36).substring(2, 9)}`);
  
  const handleAnchorClick = (e: React.MouseEvent) => {
    e.preventDefault();
    const hash = `#${headingId}`;
    
    // Update URL without page reload
    window.history.pushState(null, '', hash);
    
    // Scroll to the element
    const element = document.getElementById(headingId);
    if (element) {
      // Smooth scroll to the element
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };
  
  // Handle initial load with hash in URL
  useEffect(() => {
    // Check if the current URL hash matches this heading
    if (typeof window !== 'undefined' && window.location.hash === `#${headingId}`) {
      // Add a small delay to ensure the page has fully loaded
      setTimeout(() => {
        const element = document.getElementById(headingId);
        if (element) {
          element.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }, 100);
    }
  }, [headingId]);

  const HeadingTag = `h${level}` as keyof JSX.IntrinsicElements;
  
  return (
    <HeadingTag id={headingId} className={`group ${className} scroll-mt-16`}>
      <span className="relative inline-block">
        <a
          href={`#${headingId}`}
          onClick={handleAnchorClick}
          className="absolute -left-5 w-5 text-center opacity-0 group-hover:opacity-100 transition-opacity text-nix-primary hover:text-nix-dark font-semibold"
          aria-label={`Link to ${typeof children === 'string' ? children : 'this heading'}`}
        >
          #
        </a>
        {children}
      </span>
    </HeadingTag>
  );
};

export default AnchorHeading;
