CREATE DATABASE IF NOT EXISTS `geeklogin` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE `geeklogin`;

-- Bảng accounts (đã được cập nhật)
CREATE TABLE IF NOT EXISTS `accounts` (
    `id` integer NOT NULL AUTO_INCREMENT,
    `username` varchar(50) NOT NULL,
    `password` varchar(100) NOT NULL,
    `email` varchar(100) NOT NULL,
    `role_id` INT NOT NULL,  -- Thay user_type bằng role_id
    PRIMARY KEY (`id`),
    FOREIGN KEY (`role_id`) REFERENCES roles(id) -- Thêm foreign key đến bảng roles
) ENGINE = InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET = utf8mb4;

-- Bảng roles
CREATE TABLE IF NOT EXISTS `roles` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(50) NOT NULL
) ENGINE = InnoDB;

-- Bảng permissions
CREATE TABLE IF NOT EXISTS `permissions` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(255) NOT NULL
) ENGINE = InnoDB;

-- Bảng role_permissions
CREATE TABLE IF NOT EXISTS `role_permissions` (
    `role_id` INT,
    `permission_id` INT,
    FOREIGN KEY (`role_id`) REFERENCES roles(id),
    FOREIGN KEY (`permission_id`) REFERENCES permissions(id)
) ENGINE = InnoDB;

-- Bảng pets
CREATE TABLE `pets` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT,
    `pet_name` VARCHAR(100),
    `pet_type` VARCHAR(50),
    `pet_birthday` DATE,
    `pet_age` INT,
    `pet_gender` VARCHAR(50),
    `pet_color` VARCHAR(50),
    `pet_image` VARCHAR(255),
    FOREIGN KEY (`user_id`) REFERENCES accounts(id)
);

-- Bảng veterinarian_contacts
CREATE TABLE `veterinarian_contacts` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT,
    `contact_name` VARCHAR(100),
    `contact_gender` VARCHAR(100),
    `contact_language` VARCHAR(50),
    `contact_phone` VARCHAR(100),
    `vet_address` VARCHAR(255),
    `vet_email` VARCHAR(100),
    `vet_speciality` VARCHAR(100),
    `vet_clinic` VARCHAR(100),
    FOREIGN KEY (`user_id`) REFERENCES accounts(id)
);

-- Bảng pet_weight
CREATE TABLE IF NOT EXISTS `pet_weight` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `pet_id` INT,
    `user_id` INT,
    `weight` DECIMAL(5, 2) NOT NULL,
    `date_recorded` DATE NOT NULL,
    `notes` TEXT,
    FOREIGN KEY (`pet_id`) REFERENCES pets(id) ON DELETE CASCADE,
    FOREIGN KEY (`user_id`) REFERENCES accounts(id) ON DELETE CASCADE
);

-- Bảng pet_vaccines
CREATE TABLE IF NOT EXISTS `pet_vaccines` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `pet_id` INT,
    `user_id` INT,
    `vaccine_name` VARCHAR(100) NOT NULL,
    `dosage` INT NOT NULL,
    `date_administered` DATE NOT NULL,
    `notes` TEXT,
    FOREIGN KEY (`pet_id`) REFERENCES pets(id) ON DELETE CASCADE,
    FOREIGN KEY (`user_id`) REFERENCES accounts(id) ON DELETE CASCADE
);

-- Bảng pet_medications
CREATE TABLE IF NOT EXISTS `pet_medications` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `pet_id` INT,
    `user_id` INT,
    `medication_name` VARCHAR(100) NOT NULL,
    `dosage` VARCHAR(50) NOT NULL,
    `date_administered` DATE NOT NULL,
    `notes` TEXT,
    FOREIGN KEY (`pet_id`) REFERENCES pets(id) ON DELETE CASCADE,
    FOREIGN KEY (`user_id`) REFERENCES accounts(id) ON DELETE CASCADE
);

-- Bảng pet_allergies
CREATE TABLE IF NOT EXISTS `pet_allergies` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `pet_id` INT,
    `user_id` INT,
    `allergy` VARCHAR(100) NOT NULL,
    `cause` VARCHAR(100) NOT NULL,
    `symptoms` VARCHAR(255) NOT NULL,
    `notes` TEXT,
    FOREIGN KEY (`pet_id`) REFERENCES pets(id) ON DELETE CASCADE,
    FOREIGN KEY (`user_id`) REFERENCES accounts(id) ON DELETE CASCADE
);

-- Bảng products
CREATE TABLE IF NOT EXISTS `products` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `customer_id` INT,
    `name` VARCHAR(255) NOT NULL,
    `description` TEXT,
    `price` DECIMAL(10, 2) NOT NULL,
    `image` VARCHAR(255),
    `quantity` INT,
    FOREIGN KEY (`customer_id`) REFERENCES accounts(id)
);

-- Bảng services
CREATE TABLE IF NOT EXISTS `services` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `customer_id` INT,
    `name` VARCHAR(255) NOT NULL,
    `description` TEXT,
    `price` DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (`customer_id`) REFERENCES accounts(id)
);

-- Bảng transactions
CREATE TABLE IF NOT EXISTS `transactions` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT,
    `product_id` INT,
    `quantity` INT,
    `amount` DECIMAL(10, 2) NOT NULL,
    `status` VARCHAR(50) NOT NULL,
    `transaction_date` DATETIME NOT NULL,
    FOREIGN KEY (`user_id`) REFERENCES accounts(id),
    FOREIGN KEY (`product_id`) REFERENCES products(id)
);

-- Bảng appointments
CREATE TABLE IF NOT EXISTS `appointments` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT,
    `customer_id` INT,
    `service_id` INT,
    `appointment_date` DATETIME NOT NULL,
    `status` VARCHAR(50) NOT NULL,
    `notes` TEXT,
    FOREIGN KEY (`user_id`) REFERENCES accounts(id),
    FOREIGN KEY (`customer_id`) REFERENCES accounts(id),
    FOREIGN KEY (`service_id`) REFERENCES services(id)
);

-- Bảng reminders
CREATE TABLE IF NOT EXISTS `reminders` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT,
    `pet_id` INT,
    `title` VARCHAR(255) NOT NULL,
    `reminder_date` DATETIME NOT NULL,
    `notes` TEXT,
    FOREIGN KEY (`user_id`) REFERENCES accounts(id),
    FOREIGN KEY (`pet_id`) REFERENCES pets(id)
);

-- Thêm một số dữ liệu mẫu cho bảng roles
INSERT INTO `roles` (`name`) VALUES
('user'),
('admin'),
('customer');

-- Thêm một số dữ liệu mẫu cho bảng permissions
INSERT INTO `permissions` (`name`) VALUES
('manage_users'),
('view_transactions'),
('add_services'),
('manage_appointments'),
('add_products'),
('view_revenue');

-- Thêm một số dữ liệu mẫu cho bảng role_permissions
INSERT INTO `role_permissions` (`role_id`, `permission_id`) VALUES
(2, 1),
(2, 2),
(2, 3),
(2, 4),
(3, 2),
(3, 5),
(3, 6);

ALTER TABLE `products`
ADD COLUMN `views` INT DEFAULT 0,
ADD COLUMN `sales` INT DEFAULT 0;

ALTER TABLE `services`
ADD COLUMN `views` INT DEFAULT 0,
ADD COLUMN `sales` INT DEFAULT 0;

CREATE TABLE customers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    account_id INT UNIQUE, -- Liên kết với bảng accounts
    phone VARCHAR(20),
    address TEXT,
    description TEXT,
    total_views INT DEFAULT 0,
    total_purchases INT DEFAULT 0,
    FOREIGN KEY (account_id) REFERENCES accounts(id)
);

CREATE TABLE product_images (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT,
    image_url VARCHAR(255) NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

alter table `products`
ADD COLUMN `status` VARCHAR(50) DEFAULT 'available'

ALTER TABLE product_images ADD COLUMN is_main BOOLEAN DEFAULT FALSE;

CREATE TABLE cart (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    product_id INT,
    quantity INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES accounts(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);