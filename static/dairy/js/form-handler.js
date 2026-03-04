// Dairy Farm Management System - Form Handler
// Handles all DOM manipulation for forms

class DairyFormHandler {
    constructor() {
        this.initAll();
    }

    initAll() {
        this.initCattleForm();
        this.initMilkForm();
        this.initSaleForm();
        this.initBreedingForm();
        this.initVaccinationForm();
        this.initCostCalculators();
        this.initDatePickers();
        this.initLivePreviews();
        this.initSearchFilters();
    }

    // ==================== CATTLE FORM ====================
    initCattleForm() {
        const form = document.getElementById('cattle-form');
        if (!form) return;

        // Auto-uppercase tag number
        const tagInput = document.getElementById('id_tag_number');
        if (tagInput) {
            tagInput.addEventListener('input', (e) => {
                e.target.value = e.target.value.toUpperCase();
            });
        }

        // Age calculator
        const birthDate = document.getElementById('id_birth_date');
        const ageDisplay = document.getElementById('age-display');
        
        if (birthDate && ageDisplay) {
            birthDate.addEventListener('change', () => {
                const today = new Date();
                const birth = new Date(birthDate.value);
                const months = (today.getFullYear() - birth.getFullYear()) * 12 + 
                              (today.getMonth() - birth.getMonth());
                ageDisplay.textContent = `${months} months`;
            });
        }

        // Price validator
        const purchasePrice = document.getElementById('id_purchase_price');
        const currentValue = document.getElementById('id_current_value');
        
        if (purchasePrice && currentValue) {
            currentValue.addEventListener('input', () => {
                const purchase = parseFloat(purchasePrice.value) || 0;
                const current = parseFloat(currentValue.value) || 0;
                
                if (current < purchase * 0.5) {
                    this.showWarning('Current value is less than 50% of purchase price');
                }
            });
        }
    }

    // ==================== MILK FORM ====================
    initMilkForm() {
        const form = document.getElementById('milk-form');
        if (!form) return;

        const quantity = document.getElementById('id_quantity');
        const fat = document.getElementById('id_fat_percentage');
        const preview = document.getElementById('milk-preview');

        if (quantity && preview) {
            quantity.addEventListener('input', () => {
                const val = parseFloat(quantity.value) || 0;
                preview.innerHTML = `
                    <div class="alert alert-info">
                        <strong>${val.toFixed(2)} L</strong> of milk
                    </div>
                `;
            });
        }

        // Session-based time suggestion
        const session = document.getElementById('id_session');
        const timeField = document.getElementById('id_time');
        
        if (session && timeField) {
            session.addEventListener('change', () => {
                const times = {
                    'MORNING': '06:00',
                    'AFTERNOON': '14:00',
                    'EVENING': '18:00'
                };
                if (times[session.value]) {
                    timeField.value = times[session.value];
                }
            });
        }
    }

    // ==================== SALE FORMS ====================
    initSaleForm() {
        this.initMilkSaleForm();
        this.initCattleSaleForm();
    }

    initMilkSaleForm() {
        const form = document.getElementById('milk-sale-form');
        if (!form) return;

        const quantity = document.getElementById('id_quantity');
        const price = document.getElementById('id_price_per_liter');
        const totalDisplay = document.getElementById('total-amount');

        const updateTotal = () => {
            const qty = parseFloat(quantity?.value) || 0;
            const p = parseFloat(price?.value) || 0;
            const total = qty * p;
            
            if (totalDisplay) {
                totalDisplay.innerHTML = `
                    <div class="alert alert-success">
                        Total Amount: ৳${total.toFixed(2)}
                    </div>
                `;
            }
        };

        quantity?.addEventListener('input', updateTotal);
        price?.addEventListener('input', updateTotal);
    }

    initCattleSaleForm() {
        const form = document.getElementById('cattle-sale-form');
        if (!form) return;

        const cattleSelect = document.getElementById('id_cattle');
        const salePrice = document.getElementById('id_sale_price');
        const profitDisplay = document.getElementById('profit-preview');

        if (cattleSelect && salePrice && profitDisplay) {
            const updateProfit = async () => {
                const cattleId = cattleSelect.value;
                const price = parseFloat(salePrice.value) || 0;
                
                if (cattleId) {
                    try {
                        const response = await fetch(`/dairy/api/cattle/${cattleId}/`);
                        const data = await response.json();
                        
                        if (data.success) {
                            const purchasePrice = data.cattle.purchase_price || 0;
                            const expenses = data.cattle.total_expenses || 0;
                            const totalCost = purchasePrice + expenses;
                            const profit = price - totalCost;
                            
                            profitDisplay.innerHTML = `
                                <div class="alert ${profit >= 0 ? 'alert-success' : 'alert-danger'}">
                                    Purchase: ৳${purchasePrice} | Expenses: ৳${expenses} | 
                                    <strong>${profit >= 0 ? 'Profit' : 'Loss'}: ৳${Math.abs(profit).toFixed(2)}</strong>
                                </div>
                            `;
                        }
                    } catch (error) {
                        console.error('Error fetching cattle data:', error);
                    }
                }
            };

            cattleSelect.addEventListener('change', updateProfit);
            salePrice.addEventListener('input', updateProfit);
        }
    }

    // ==================== BREEDING FORM ====================
    initBreedingForm() {
        const form = document.getElementById('breeding-form');
        if (!form) return;

        const breedingDate = document.getElementById('breeding_date');
        const pregnantToggle = document.getElementById('pregnant_toggle');
        const expectedDate = document.getElementById('expected_date');
        const calvingSection = document.getElementById('calving-section');

        // Calculate expected calving date
        if (breedingDate && pregnantToggle && expectedDate) {
            const updateExpectedDate = () => {
                if (pregnantToggle.checked && breedingDate.value) {
                    const date = new Date(breedingDate.value);
                    date.setDate(date.getDate() + 280);
                    const year = date.getFullYear();
                    const month = String(date.getMonth() + 1).padStart(2, '0');
                    const day = String(date.getDate()).padStart(2, '0');
                    expectedDate.value = `${year}-${month}-${day}`;
                }
            };

            breedingDate.addEventListener('change', updateExpectedDate);
            pregnantToggle.addEventListener('change', updateExpectedDate);
        }

        // Show/hide calving section
        const statusSelect = document.getElementById('id_status');
        if (statusSelect && calvingSection) {
            statusSelect.addEventListener('change', () => {
                calvingSection.style.display = 
                    statusSelect.value === 'CALVED' ? 'block' : 'none';
            });
        }

        // Sire recommendation based on breed
        const breedField = document.getElementById('id_breed');
        const sireField = document.getElementById('id_sire');
        
        if (breedField && sireField) {
            breedField.addEventListener('change', async () => {
                const breed = breedField.value;
                if (breed) {
                    try {
                        const response = await fetch(`/dairy/api/sires/?breed=${breed}`);
                        const data = await response.json();
                        
                        // Update sire options
                        sireField.innerHTML = '<option value="">Select Sire</option>';
                        data.sires.forEach(sire => {
                            sireField.innerHTML += `<option value="${sire.id}">${sire.tag_number} - ${sire.breed}</option>`;
                        });
                    } catch (error) {
                        console.error('Error fetching sires:', error);
                    }
                }
            });
        }
    }

    // ==================== VACCINATION FORM ====================
    initVaccinationForm() {
        const form = document.getElementById('vaccination-form');
        if (!form) return;

        const completeToggle = document.getElementById('complete_toggle');
        const adminDate = document.getElementById('id_administered_date');
        const adminSection = document.getElementById('administration-section');

        if (completeToggle && adminSection) {
            completeToggle.addEventListener('change', () => {
                if (completeToggle.checked) {
                    adminSection.style.display = 'block';
                    if (!adminDate.value) {
                        const today = new Date().toISOString().split('T')[0];
                        adminDate.value = today;
                    }
                } else {
                    adminSection.style.display = 'none';
                    adminDate.value = '';
                }
            });
        }

        // Batch number suggestion
        const vaccineType = document.getElementById('id_vaccine_type');
        const batchField = document.getElementById('id_batch_number');
        
        if (vaccineType && batchField) {
            vaccineType.addEventListener('change', () => {
                const year = new Date().getFullYear();
                const suggestions = {
                    'FMD': `FMD-${year}-001`,
                    'BQ': `BQ-${year}-001`,
                    'HS': `HS-${year}-001`,
                    'BRU': `BRU-${year}-001`,
                    'IBR': `IBR-${year}-001`
                };
                
                if (suggestions[vaccineType.value] && !batchField.value) {
                    batchField.value = suggestions[vaccineType.value];
                }
            });
        }
    }

    // ==================== COST CALCULATORS ====================
    initCostCalculators() {
        this.initFeedingCost();
        this.initExpenseTracker();
    }

    initFeedingCost() {
        const form = document.getElementById('feeding-form');
        if (!form) return;

        const quantity = document.getElementById('id_quantity');
        const costPerKg = document.getElementById('id_cost_per_kg');
        const totalDisplay = document.getElementById('total-cost-display');

        const updateTotal = () => {
            const qty = parseFloat(quantity?.value) || 0;
            const cost = parseFloat(costPerKg?.value) || 0;
            const total = qty * cost;
            
            if (totalDisplay) {
                totalDisplay.innerHTML = `
                    <div class="alert alert-info">
                        Total Cost: ৳${total.toFixed(2)}
                    </div>
                `;
            }
        };

        quantity?.addEventListener('input', updateTotal);
        costPerKg?.addEventListener('input', updateTotal);
    }

    initExpenseTracker() {
        const form = document.getElementById('expense-form');
        if (!form) return;

        const amount = document.getElementById('id_amount');
        const category = document.getElementById('id_category');
        const monthlyBudget = document.getElementById('monthly-budget');

        if (amount && category && monthlyBudget) {
            const checkBudget = async () => {
                const catId = category.value;
                const amt = parseFloat(amount.value) || 0;
                
                if (catId && amt > 0) {
                    try {
                        const response = await fetch(`/dairy/api/budget-check/?category=${catId}&amount=${amt}`);
                        const data = await response.json();
                        
                        if (data.exceeds_budget) {
                            this.showWarning(`This expense exceeds your monthly budget by ৳${data.excess}`);
                        }
                    } catch (error) {
                        console.error('Error checking budget:', error);
                    }
                }
            };

            amount.addEventListener('input', checkBudget);
            category.addEventListener('change', checkBudget);
        }
    }

    // ==================== DATE PICKERS ====================
    initDatePickers() {
        // Set max date to today for all date inputs
        const today = new Date().toISOString().split('T')[0];
        document.querySelectorAll('input[type="date"]').forEach(input => {
            if (!input.getAttribute('max')) {
                input.setAttribute('max', today);
            }
        });

        // Date range validation
        const startDate = document.getElementById('start_date');
        const endDate = document.getElementById('end_date');
        
        if (startDate && endDate) {
            startDate.addEventListener('change', () => {
                endDate.setAttribute('min', startDate.value);
            });
            
            endDate.addEventListener('change', () => {
                if (startDate.value && endDate.value < startDate.value) {
                    this.showError('End date cannot be before start date');
                    endDate.value = '';
                }
            });
        }
    }

    // ==================== LIVE PREVIEWS ====================
    initLivePreviews() {
        // Cattle preview
        const cattleForm = document.getElementById('cattle-form');
        if (cattleForm) {
            const previewBtn = document.getElementById('preview-cattle');
            if (previewBtn) {
                previewBtn.addEventListener('click', () => {
                    this.showCattlePreview();
                });
            }
        }
    }

    showCattlePreview() {
        const data = {
            tag: document.getElementById('id_tag_number')?.value || 'N/A',
            name: document.getElementById('id_name')?.value || 'Unnamed',
            type: document.getElementById('id_cattle_type')?.options[
                document.getElementById('id_cattle_type')?.selectedIndex
            ]?.text || 'N/A',
            breed: document.getElementById('id_breed')?.options[
                document.getElementById('id_breed')?.selectedIndex
            ]?.text || 'N/A',
            gender: document.getElementById('id_gender')?.options[
                document.getElementById('id_gender')?.selectedIndex
            ]?.text || 'N/A',
            weight: document.getElementById('id_weight')?.value || 'Not set',
            price: document.getElementById('id_purchase_price')?.value || 'Not set'
        };

        const previewHtml = `
            <div class="modal fade" id="previewModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header bg-primary text-white">
                            <h5 class="modal-title">Cattle Preview</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <table class="table">
                                <tr><th>Tag Number:</th><td>${data.tag}</td></tr>
                                <tr><th>Name:</th><td>${data.name}</td></tr>
                                <tr><th>Type:</th><td>${data.type}</td></tr>
                                <tr><th>Breed:</th><td>${data.breed}</td></tr>
                                <tr><th>Gender:</th><td>${data.gender}</td></tr>
                                <tr><th>Weight:</th><td>${data.weight} kg</td></tr>
                                <tr><th>Purchase Price:</th><td>৳${data.price}</td></tr>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        `;

        if (!document.getElementById('previewModal')) {
            document.body.insertAdjacentHTML('beforeend', previewHtml);
        }
        
        const modal = new bootstrap.Modal(document.getElementById('previewModal'));
        modal.show();
    }

    // ==================== SEARCH FILTERS ====================
    initSearchFilters() {
        const searchForm = document.getElementById('search-form');
        if (!searchForm) return;

        let timeout = null;
        const searchInput = document.getElementById('search-input');
        
        if (searchInput) {
            searchInput.addEventListener('keyup', () => {
                clearTimeout(timeout);
                timeout = setTimeout(() => {
                    searchForm.submit();
                }, 500);
            });
        }

        // Dynamic filter updates
        const filters = document.querySelectorAll('.dynamic-filter');
        filters.forEach(filter => {
            filter.addEventListener('change', () => {
                searchForm.submit();
            });
        });
    }

    // ==================== UTILITY FUNCTIONS ====================
    showWarning(message) {
        const toast = this.createToast(message, 'warning');
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }

    showError(message) {
        const toast = this.createToast(message, 'danger');
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }

    showSuccess(message) {
        const toast = this.createToast(message, 'success');
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }

    createToast(message, type) {
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0 position-fixed top-0 end-0 m-3`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        toast.style.zIndex = '9999';
        
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        return toast;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.dairyForms = new DairyFormHandler();
});