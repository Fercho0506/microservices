# ============================================================
# BITE.co Microservices Infrastructure
# AWS Academy Compatible — uses LabRole, no custom IAM
# ============================================================

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# --- Data Sources ---
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# ============================================================
# Security Groups
# ============================================================

resource "aws_security_group" "kong_sg" {
  name        = "bite-kong-sg"
  description = "Kong API Gateway SG"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Kong proxy port"
  }

  ingress {
    from_port   = 8443
    to_port     = 8443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Kong HTTPS proxy"
  }

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "SSH"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "bite-kong-sg" }
}

resource "aws_security_group" "services_sg" {
  name        = "bite-services-sg"
  description = "BITE Microservices SG"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port   = 8080
    to_port     = 8082
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Microservice ports"
  }

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "SSH"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "bite-services-sg" }
}

resource "aws_security_group" "rds_sg" {
  name        = "bite-rds-sg"
  description = "RDS PostgreSQL SG"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.services_sg.id]
    description     = "PostgreSQL from services"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "bite-rds-sg" }
}

resource "aws_security_group" "elasticache_sg" {
  name        = "bite-elasticache-sg"
  description = "ElastiCache Redis SG"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.services_sg.id]
    description     = "Redis from services"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "bite-elasticache-sg" }
}

# ============================================================
# RDS PostgreSQL (Amazon RDS - Business Data)
# ============================================================

resource "aws_db_subnet_group" "bite_db_subnet" {
  name       = "bite-db-subnet-group"
  subnet_ids = data.aws_subnets.default.ids
  tags       = { Name = "bite-db-subnet-group" }
}

resource "aws_db_instance" "finops_db" {
  identifier             = "bite-finops-db"
  engine                 = "postgres"
  engine_version         = "15.4"
  instance_class         = var.db_instance_class
  allocated_storage      = 20
  db_name                = "finops_db"
  username               = var.db_username
  password               = var.db_password
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
  db_subnet_group_name   = aws_db_subnet_group.bite_db_subnet.name
  publicly_accessible    = false
  skip_final_snapshot    = true
  multi_az               = false

  tags = { Name = "bite-finops-db" }
}

# ============================================================
# ElastiCache Redis (for FinOps query caching)
# ============================================================

resource "aws_elasticache_subnet_group" "redis_subnet" {
  name       = "bite-redis-subnet"
  subnet_ids = data.aws_subnets.default.ids
}

resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "bite-redis"
  engine               = "redis"
  node_type            = "cache.t3.small"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
  security_group_ids   = [aws_security_group.elasticache_sg.id]
  subnet_group_name    = aws_elasticache_subnet_group.redis_subnet.name

  tags = { Name = "bite-redis" }
}

# ============================================================
# EC2 Instances
# ============================================================

# Kong API Gateway
resource "aws_instance" "kong" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name               = var.key_pair_name
  vpc_security_group_ids = [aws_security_group.kong_sg.id]

  # AWS Academy: use LabRole instance profile — no IAM role creation needed
  iam_instance_profile = "LabInstanceProfile"

  user_data = base64encode(templatefile("${path.module}/scripts/kong_init.sh", {
    finops_ip      = aws_instance.finops.private_ip
    integration_ip = aws_instance.integration.private_ip
    cron_ip        = aws_instance.cron_worker.private_ip
  }))

  tags = { Name = "bite-kong" }
}

# FinOps Service
resource "aws_instance" "finops" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name               = var.key_pair_name
  vpc_security_group_ids = [aws_security_group.services_sg.id]
  iam_instance_profile   = "LabInstanceProfile"

  user_data = base64encode(templatefile("${path.module}/scripts/finops_init.sh", {
    db_host       = aws_db_instance.finops_db.address
    db_password   = var.db_password
    redis_host    = aws_elasticache_cluster.redis.cache_nodes[0].address
    auth0_domain  = var.auth0_domain
    auth0_audience = var.auth0_audience
  }))

  tags = { Name = "bite-finops" }
}

# Cloud Integration Service
resource "aws_instance" "integration" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name               = var.key_pair_name
  vpc_security_group_ids = [aws_security_group.services_sg.id]
  iam_instance_profile   = "LabInstanceProfile"

  user_data = base64encode(templatefile("${path.module}/scripts/integration_init.sh", {
    db_host     = aws_db_instance.finops_db.address
    db_password = var.db_password
    mongo_host  = "localhost"
  }))

  tags = { Name = "bite-integration" }
}

# CRON Worker Service
resource "aws_instance" "cron_worker" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name               = var.key_pair_name
  vpc_security_group_ids = [aws_security_group.services_sg.id]
  iam_instance_profile   = "LabInstanceProfile"

  user_data = base64encode(templatefile("${path.module}/scripts/cron_init.sh", {
    integration_ip = aws_instance.integration.private_ip
    finops_ip      = aws_instance.finops.private_ip
    db_host        = aws_db_instance.finops_db.address
    db_password    = var.db_password
  }))

  tags = { Name = "bite-cron-worker" }
}

# ============================================================
# Outputs
# ============================================================

output "kong_public_ip" {
  description = "Kong API Gateway public IP — use this to call the APIs"
  value       = aws_instance.kong.public_ip
}

output "finops_private_ip" {
  value = aws_instance.finops.private_ip
}

output "integration_private_ip" {
  value = aws_instance.integration.private_ip
}

output "cron_private_ip" {
  value = aws_instance.cron_worker.private_ip
}

output "rds_endpoint" {
  value = aws_db_instance.finops_db.address
}

output "redis_endpoint" {
  value = aws_elasticache_cluster.redis.cache_nodes[0].address
}
