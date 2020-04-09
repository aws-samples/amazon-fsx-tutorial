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

# IOR write - from one instance
mpirun --npernode 4 --oversubscribe ior --posix.odirect -t 1m -b 1320m -g -v -w -i 1 -F -k -D 0 -o /fsx/ior.bin

# IOR read - from all instances
mpirun --npernode 4 --oversubscribe ior --posix.odirect -t 1m -g -r -i 1000000 -F -k -D 0 -z -o /fsx/ior.bin



