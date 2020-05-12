# install linux client
sudo amazon-linux-extras install -y lustre2.10

# install utility packages
sudo amazon-linux-extras install -y epel
sudo yum groupinstall -y "Development Tools"
sudo yum install -y tree nload git libaio-devel openmpi openmpi-devel

# install ior
git clone https://github.com/hpc/ior.git
export PATH=$PATH:/usr/lib64/openmpi/bin
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/lib64/openmpi/lib/
cd ior
./bootstrap
./configure
make
sudo cp src/ior /usr/local/bin
cd

# mount FSx for Lustre
sudo mkdir -p /fsx
sudo mount -t lustre -o noatime,flock <fsid>.fsx.<region>.amazonaws.com@tcp:/<mountname> /fsx 
sudo chown ec2-user:ec2-user /fsx



## write test

# IOR - write test from all instances
instance_id=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
mpirun --npernode 8 --oversubscribe ior --posix.odirect -t 1m -b 1m -s 16384 -g -v -w -i 100 -F -k -D 0 -o /fsx/ior-${instance_id}.bin



## read test

# IOR - write test from one instance
mpirun --npernode 8 --oversubscribe ior --posix.odirect -t 1m -b 1m -s 8192 -g -v -w -i 1 -F -k -D 0 -o /fsx/ior.bin

# IOR - read test from all instances
mpirun --npernode 8 --oversubscribe ior --posix.odirect -t 1m -b 1m -s 8192 -g -r -i 10000 -F -k -D 60 -z -o /fsx/ior.bin



## in-memory cache read test

# IOR - write test from one instance
mpirun --npernode 8 --oversubscribe ior --posix.odirect -t 1m -b 1m -s 675 -g -v -w -i 1 -F -k -D 0 -o /fsx/ior.bin

# IOR - read test from all instances
mpirun --npernode 8 --oversubscribe ior --posix.odirect -t 1m -b 1m -g -r -i 2000000 -F -k -D 0 -z -o /fsx/ior.bin



