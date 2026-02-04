# AWS Meep FDTD Simulation Quick Reference

Your quota: 256 vCPUs (approved)

---

## 1. Instance Selection

| Array Size | Resolution | Est. RAM | Recommended Instance | vCPUs | Cost (Spot) |
|------------|------------|----------|---------------------|-------|-------------|
| 9x9        | 20-30      | ~64 GB   | `r7i.8xlarge`       | 32    | $0.70/hr    |
| 27x27      | 20-30      | ~256 GB  | `r7i.16xlarge`      | 64    | $1.40/hr    |
| 81x81      | 20         | ~512 GB  | `r7i.24xlarge`      | 96    | $2.10/hr    |
| 81x81      | 30         | ~1 TB    | `r7i.48xlarge`      | 192   | $4.20/hr    |

**Rule of thumb:** Memory scales as O(N^2 * resolution^2). Double the array size = 4x the memory.

---

## 2. EC2 Launch (Console)

1. **AMI:** Ubuntu 22.04 LTS (ami-0c7217cdde317cfec in us-east-1)
2. **Instance type:** Select from table above
3. **Key pair:** Use existing or create new (download .pem)
4. **Security group:** Allow SSH (port 22) from your IP
5. **Storage:** 100 GB gp3 (default is too small for HDF5 output)
6. **Request Spot:** Under "Advanced" > Purchase option > Spot (60-70% savings)

---

## 3. Environment Setup

SSH into instance, then:

```bash
# Update and install system packages
sudo apt update && sudo apt install -y \
    python3-pip python3-venv \
    libopenmpi-dev openmpi-bin \
    python3-h5py h5utils \
    python3-matplotlib python3-numpy

# Install Meep via conda (recommended for MPI support)
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh -b -p $HOME/miniconda
eval "$($HOME/miniconda/bin/conda shell.bash hook)"

# Create Meep environment with MPI
conda create -n meep -c conda-forge pymeep=*=mpi_mpich* -y
conda activate meep

# Verify MPI works
mpirun -np 4 python3 -c "import meep; print(f'Meep {meep.__version__} with MPI')"
```

---

## 4. Transfer Code

**Option A: scp (simple)**
```bash
# From your local machine
scp -i ~/.ssh/your-key.pem -r \
    /home/jackwayne/Desktop/Optical_computing/Research/programs/simulations \
    ubuntu@<EC2-IP>:~/simulation/
```

**Option B: git clone (if repo is pushed)**
```bash
# On EC2
git clone https://github.com/yourusername/Optical_computing.git
cd Optical_computing/Research/programs/simulations
```

---

## 5. Running Simulations with MPI

```bash
# Activate environment
conda activate meep
cd ~/simulation

# Basic MPI run (use N-2 cores to leave room for OS)
mpirun -np 62 python3 -u clock_distribution_sim.py --array-size 27

# With specific flags
mpirun --use-hwthread-cpus -np 94 python3 -u kerr_resonator_sim.py --sweep-power

# Background with logging (for long runs)
nohup mpirun -np 62 python3 -u clock_distribution_sim.py --array-size 81 \
    > simulation.log 2>&1 &
tail -f simulation.log
```

**MPI flags explained:**
- `-np N`: Number of processes (use vCPUs - 2)
- `--use-hwthread-cpus`: Use all hardware threads
- `-u` (python): Unbuffered output for real-time logs

---

## 6. Your Simulations

| Simulation | Purpose | Typical Args |
|------------|---------|--------------|
| `clock_distribution_sim.py` | Clock skew validation | `--array-size 9/27/81 --analyze-skew` |
| `kerr_resonator_sim.py` | 617 MHz clock generation | `--sweep-power` or `--time-domain` |
| `sfg_wavelength_test.py` | SFG mixer output validation | `--all-combinations` |
| `mzi_switch_sim.py` | MZI optical switch | default |
| `awg_demux_sim.py` | AWG demultiplexer | default |

---

## 7. Download Results and Terminate

```bash
# From local machine - download results
scp -i ~/.ssh/your-key.pem -r ubuntu@<EC2-IP>:~/simulation/*.h5 \
    /home/jackwayne/Desktop/Optical_computing/Research/data/cloud_results/

scp -i ~/.ssh/your-key.pem -r ubuntu@<EC2-IP>:~/simulation/*.png \
    /home/jackwayne/Desktop/Optical_computing/Research/data/cloud_results/

# IMPORTANT: Terminate instance when done!
# Via console or:
aws ec2 terminate-instances --instance-ids <instance-id>
```

---

## 8. Quick Cost Estimate

| Run Time | 9x9 (32 vCPU) | 27x27 (64 vCPU) | 81x81 (96 vCPU) |
|----------|---------------|-----------------|-----------------|
| 1 hour   | $0.70         | $1.40           | $2.10           |
| 4 hours  | $2.80         | $5.60           | $8.40           |
| 8 hours  | $5.60         | $11.20          | $16.80          |

*Spot prices. On-demand is ~3x higher.*

---

## Troubleshooting

**MPI out of memory:**
- Reduce resolution or array size
- Use larger instance

**Spot instance terminated:**
- Spot instances can be interrupted (rare)
- Use on-demand for critical multi-hour runs

**SSH connection refused:**
- Instance still booting (wait 60s)
- Security group missing SSH rule
- Wrong IP (check EC2 console)
