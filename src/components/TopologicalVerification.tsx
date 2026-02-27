import { AlertCircle, Layers, PlayCircle, ShieldCheck } from 'lucide-react';
import { KnotData, KnotVerificationResponse } from '../types';
import { useState } from 'react';

interface Props {
  activeKnot: KnotData | null;
  onVerified: () => void;
}

function isVerifiedStatus(status: KnotData['status'] | undefined) {
  return status === 'verified' || status === 'compiled' || status === 'executed';
}

export default function TopologicalVerification({ activeKnot, onVerified }: Props) {
  const [backendUrl, setBackendUrl] = useState('http://localhost:8000');
  const [isVerifying, setIsVerifying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [verificationResult, setVerificationResult] = useState<KnotVerificationResponse | null>(null);
  const isVerified = isVerifiedStatus(activeKnot?.status) || verificationResult?.is_verified === true;

  const readErrorDetail = async (response: Response, fallbackMessage: string) => {
    let detail = fallbackMessage;
    try {
      const errData = await response.json();
      if (typeof errData?.detail === 'string' && errData.detail.trim()) {
        detail = errData.detail;
      }
    } catch {
      // Keep fallback when server response body is not JSON.
    }
    return detail;
  };

  const handleVerify = async () => {
    if (!activeKnot?.braidWord?.trim()) {
      setError('A braid word is required before verification.');
      return;
    }

    setIsVerifying(true);
    setError(null);

    try {
      const normalizedBackendUrl = backendUrl.trim().replace(/\/$/, '');
      const response = await fetch(`${normalizedBackendUrl}/api/knot/verify`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          braid_word: activeKnot.braidWord,
        }),
      });

      if (!response.ok) {
        const detail = await readErrorDetail(response, 'Failed to verify braid topology.');
        if (response.status === 422) {
          throw new Error(`Input validation failed: ${detail}`);
        }
        throw new Error(`Server error (${response.status}): ${detail}`);
      }

      const payload = (await response.json()) as KnotVerificationResponse;
      setVerificationResult(payload);
      if (payload.is_verified) {
        onVerified();
      } else {
        setError(payload.detail);
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        if (err.name === 'TypeError') {
          setError(`Could not reach the Python backend at ${backendUrl.trim() || 'the configured address'}.`);
        } else {
          setError(err.message || 'Failed to verify braid topology.');
        }
      } else {
        setError('Failed to verify braid topology.');
      }
    } finally {
      setIsVerifying(false);
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div>
        <h2 className="text-2xl font-semibold text-zinc-100 tracking-tight">2. Topological Verification</h2>
        <p className="text-zinc-400 mt-2">
          Verify the braid word with backend computed checks and evidence before circuit synthesis.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
            <div className="flex items-center gap-2 mb-6">
              <Layers className="w-5 h-5 text-emerald-500" />
              <h3 className="font-medium text-zinc-200">Verification Engine</h3>
            </div>
            
            <div className="space-y-4">
              {error && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-md p-3 flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                  <p className="text-xs text-red-300">{error}</p>
                </div>
              )}

              {verificationResult && !error && (
                <div className="bg-zinc-800/50 border border-zinc-700 rounded-md p-3">
                  <p className="text-xs text-zinc-300">{verificationResult.detail}</p>
                </div>
              )}

              <div>
                <label className="block text-xs font-medium text-zinc-500 uppercase tracking-wider mb-2">
                  Input Braid Word
                </label>
                <div className="bg-[#0a0a0a] border border-zinc-800 rounded-md px-4 py-2.5 text-zinc-200 font-mono text-sm">
                  {activeKnot?.braidWord || 'No braid word available'}
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-500 uppercase tracking-wider mb-2">
                  Python Backend URL
                </label>
                <input
                  type="text"
                  value={backendUrl}
                  onChange={(e) => setBackendUrl(e.target.value)}
                  className="w-full bg-[#0a0a0a] border border-zinc-800 rounded-md px-4 py-2.5 text-zinc-200 font-mono text-sm focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/50 transition-all"
                  placeholder="http://localhost:8000"
                />
              </div>
              
              <button
                onClick={handleVerify}
                disabled={isVerifying || !activeKnot?.braidWord?.trim()}
                className="w-full bg-emerald-500 hover:bg-emerald-600 text-emerald-950 font-medium py-2.5 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {isVerifying ? (
                  <span className="animate-pulse">Running Verification...</span>
                ) : (
                  <>
                    <PlayCircle className="w-4 h-4" />
                    Verify Topological Mapping
                  </>
                )}
              </button>
            </div>
          </div>

          {isVerified && (
            <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <div className="flex items-center gap-3 text-emerald-400 mb-4">
                <ShieldCheck className="w-5 h-5" />
                <h3 className="font-medium">Verification Passed</h3>
              </div>
              <p className="text-sm text-emerald-400/80 leading-relaxed">
                The braid word passed computed topological checks and can proceed to circuit generation.
                Ready for circuit synthesis.
              </p>
            </div>
          )}
        </div>

        <div className="lg:col-span-2 bg-[#111111] border border-zinc-800 rounded-xl p-6 flex flex-col min-h-[400px]">
          <h3 className="font-medium text-zinc-200 mb-6">Verification Output</h3>
          
          <div className="flex-1 border border-zinc-800 rounded-md bg-[#0a0a0a] relative overflow-hidden flex items-center justify-center">
            {isVerifying ? (
              <div className="absolute inset-0 flex items-center justify-center bg-zinc-900/50 backdrop-blur-sm z-10 pointer-events-none">
                <div className="flex flex-col items-center gap-4">
                  <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
                  <span className="text-sm font-medium text-emerald-400">Computing Verification Evidence...</span>
                </div>
              </div>
            ) : null}
            
            {isVerified ? (
              <div className="w-full h-full p-8 flex items-center justify-center">
                <svg viewBox="0 0 400 200" className="w-full max-w-md opacity-80">
                  <path d="M 50 50 Q 150 50 200 100 T 350 150" fill="none" stroke="#10b981" strokeWidth="4" strokeLinecap="round" />
                  <path d="M 50 150 Q 150 150 200 100 T 350 50" fill="none" stroke="#3b82f6" strokeWidth="4" strokeLinecap="round" />
                  <path d="M 50 100 L 350 100" fill="none" stroke="#8b5cf6" strokeWidth="4" strokeLinecap="round" strokeDasharray="8 8" />
                  <circle cx="200" cy="100" r="8" fill="#f59e0b" />
                </svg>
              </div>
            ) : verificationResult ? (
              <div className="w-full h-full p-6">
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="bg-zinc-900 border border-zinc-800 rounded-md p-3">
                    <div className="text-zinc-500 text-xs uppercase tracking-wider">Token Count</div>
                    <div className="text-zinc-200 font-mono mt-1">{verificationResult.evidence.token_count}</div>
                  </div>
                  <div className="bg-zinc-900 border border-zinc-800 rounded-md p-3">
                    <div className="text-zinc-500 text-xs uppercase tracking-wider">Inverse Count</div>
                    <div className="text-zinc-200 font-mono mt-1">{verificationResult.evidence.inverse_count}</div>
                  </div>
                  <div className="bg-zinc-900 border border-zinc-800 rounded-md p-3">
                    <div className="text-zinc-500 text-xs uppercase tracking-wider">Net Writhe</div>
                    <div className="text-zinc-200 font-mono mt-1">{verificationResult.evidence.net_writhe}</div>
                  </div>
                  <div className="bg-zinc-900 border border-zinc-800 rounded-md p-3">
                    <div className="text-zinc-500 text-xs uppercase tracking-wider">Generator Switches</div>
                    <div className="text-zinc-200 font-mono mt-1">{verificationResult.evidence.generator_switches}</div>
                  </div>
                  <div className="bg-zinc-900 border border-zinc-800 rounded-md p-3">
                    <div className="text-zinc-500 text-xs uppercase tracking-wider">s1 / s2 Count</div>
                    <div className="text-zinc-200 font-mono mt-1">
                      {verificationResult.evidence.generator_counts.s1} / {verificationResult.evidence.generator_counts.s2}
                    </div>
                  </div>
                  <div className="bg-zinc-900 border border-zinc-800 rounded-md p-3">
                    <div className="text-zinc-500 text-xs uppercase tracking-wider">Strand Connectivity</div>
                    <div className="text-zinc-200 font-mono mt-1">{verificationResult.evidence.strand_connectivity}</div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-zinc-600 text-sm">
                Awaiting verification...
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
