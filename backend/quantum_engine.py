import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler

def run_knot_experiment(token: str, backend_name: str, braid_word: str, shots: int, optimization_level: int = 3):
    """
    Submits a knot evaluation circuit to IBM Quantum hardware using Qiskit Runtime.
    """
    # 1. Authenticate with IBM Quantum
    service = QiskitRuntimeService(channel="ibm_quantum", token=token)
    
    # 2. Select Backend
    if backend_name == "least_busy":
        backend = service.least_busy(operational=True, simulator=False)
    else:
        try:
            backend = service.backend(backend_name)
        except Exception:
            # Fallback to least busy if specific backend is unavailable
            backend = service.least_busy(operational=True, simulator=False)

    # 3. Construct the Hadamard Test Circuit for the Braid Word
    # This is a simplified representation of the Jones Polynomial evaluation
    # at the 5th root of unity.
    num_qubits = 3 # 1 ancilla + 2 data qubits for a simple braid
    qc = QuantumCircuit(num_qubits, 1)
    
    # Initialize ancilla in superposition
    qc.h(0)
    
    # Apply Yang-Baxter unitaries (simplified as controlled rotations)
    # The actual mapping depends on the specific braid word generators (s1, s2, etc.)
    theta = 2 * np.pi / 5 # 5th root of unity
    
    # Example braid interactions
    qc.cx(1, 2)
    qc.cp(theta, 0, 1) # Controlled phase from ancilla
    qc.cx(1, 2)
    qc.cp(-theta, 0, 2)
    
    # Close the Hadamard test
    qc.h(0)
    
    # Measure the ancilla
    qc.measure(0, 0)
    
    # 4. Transpile for the specific heavy-hex topology
    transpiled_qc = transpile(qc, backend=backend, optimization_level=optimization_level)
    
    # 5. Execute using the V2 Sampler primitive
    sampler = Sampler(backend=backend)
    job = sampler.run([transpiled_qc], shots=shots)
    
    # 6. Wait for results
    result = job.result()
    pub_result = result[0]
    
    # Extract measurement counts
    counts = pub_result.data.c.get_counts()
    
    # Calculate expectation value <Z>
    zero_count = counts.get('0', 0)
    one_count = counts.get('1', 0)
    total = zero_count + one_count
    expectation = (zero_count - one_count) / total if total > 0 else 0
    
    # Calculate a simplified Jones polynomial coefficient based on the expectation
    # V(t) = -t^-4 + t^-3 + t^-1 (Mock calculation based on expectation)
    jones_poly = f"V(t) = {expectation:.3f}t^-4 + t^-3 + t^-1"

    # Format output for the React frontend
    formatted_counts = [
        {"name": k.zfill(2), "probability": v / total} 
        for k, v in counts.items()
    ]
    
    return {
        "job_id": job.job_id(),
        "backend": backend.name,
        "counts": formatted_counts,
        "expectation_value": expectation,
        "jones_polynomial": jones_poly,
        "status": "COMPLETED"
    }
