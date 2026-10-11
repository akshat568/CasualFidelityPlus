import React, { useEffect } from 'react';
import { X } from 'lucide-react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  maxWidth?: string;
  footer?: React.ReactNode;
  hideDefaultFooter?: boolean;
  children: React.ReactNode;
}

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  maxWidth = 'max-w-3xl',
  footer,
  hideDefaultFooter = false,
  children
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.body.style.overflow = 'unset';
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs animate-fade-in">
      <div className={`bg-white rounded-2xl border border-[#E5E7EB] shadow-2xl ${maxWidth} w-full max-h-[90vh] flex flex-col overflow-hidden`}>
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-[#E5E7EB] flex items-center justify-between bg-[#F8FAFC]">
          <h3 className="text-lg font-bold text-[#1F2937] truncate pr-2">{title}</h3>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-[#64748B] hover:bg-[#E5E7EB] hover:text-[#1F2937] transition-colors cursor-pointer shrink-0"
            aria-label="Close modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-4 text-sm text-[#1F2937] flex-1">{children}</div>
        {/* Modal Footer */}
        {!hideDefaultFooter && (
          <div className="px-6 py-3 border-t border-[#E5E7EB] bg-[#F8FAFC] flex items-center justify-between">
            {footer ? (
              footer
            ) : (
              <div className="w-full flex justify-end">
                <button
                  onClick={onClose}
                  className="px-4 py-2 text-xs font-semibold bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors cursor-pointer"
                >
                  Close
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
