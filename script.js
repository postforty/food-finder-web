document.addEventListener("DOMContentLoaded", () => {
  const cardContainer = document.getElementById("restaurant-cards");
  const modal = document.getElementById("modal");
  const closeModalButton = document.getElementById("close-modal");
  const filtersContainer = document.getElementById("category-filters");
  const searchInput = document.getElementById("search-input");
  const rouletteButton = document.getElementById("random-roulette");

  let allRestaurants = []; // To store all restaurant data
  let debounceTimer;

  if (
    !cardContainer ||
    !modal ||
    !closeModalButton ||
    !filtersContainer ||
    !searchInput
  ) {
    console.error("Error: A critical element was not found in the DOM!");
    return;
  }

  // Fetch data, set up filters, and build cards
  fetch("list.json")
    .then((response) => response.json())
    .then((data) => {
      allRestaurants = data.filter((item) => item.title);
      setupCategoryFilters();
      renderCards(allRestaurants); // Initial render of all cards
    })
    .catch((error) => {
      console.error("Error fetching restaurant data:", error);
      cardContainer.innerHTML =
        '<p class="error-message">데이터를 불러오는 데 실패했습니다.</p>';
    });

  function debounce(func, delay) {
    return function (...args) {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        func.apply(this, args);
      }, delay);
    };
  }

  function applyFilters() {
    const searchTerm = searchInput.value.toLowerCase();
    const activeCategoryButton =
      filtersContainer.querySelector(".filter-btn.active");
    const selectedCategory = activeCategoryButton
      ? activeCategoryButton.dataset.category
      : "전체";

    let filteredRestaurants = allRestaurants;

    // 1. Filter by category
    if (selectedCategory !== "전체") {
      filteredRestaurants = filteredRestaurants.filter(
        (r) => r.category === selectedCategory
      );
    }

    // 2. Filter by search term
    if (searchTerm) {
      filteredRestaurants = filteredRestaurants.filter((r) =>
        r.title.toLowerCase().includes(searchTerm)
      );
    }

    renderCards(filteredRestaurants);
  }

  function setupCategoryFilters() {
    const categoryBtnGroup = filtersContainer.querySelector(
      ".category-btn-group"
    );
    const rouletteBtn = categoryBtnGroup.querySelector("#random-roulette");
    const categories = [
      "전체",
      ...new Set(allRestaurants.map((r) => r.category).filter(Boolean)),
    ];
    // .category-btn-group 내에서, 룰렛 버튼 외 모두 제거 (버튼 재생성 시 기존 카테고리만 삭제)
    Array.from(categoryBtnGroup.children).forEach((child) => {
      if (child !== rouletteBtn) categoryBtnGroup.removeChild(child);
    });
    categories.forEach((category) => {
      const button = document.createElement("button");
      button.className = "filter-btn";
      button.textContent = category;
      button.dataset.category = category;
      if (category === "전체") {
        button.classList.add("active");
      }
      categoryBtnGroup.insertBefore(button, rouletteBtn);
    });

    categoryBtnGroup.addEventListener("click", (e) => {
      if (e.target.classList.contains("filter-btn")) {
        const current = categoryBtnGroup.querySelector(".filter-btn.active");
        if (current) current.classList.remove("active");
        e.target.classList.add("active");
        applyFilters();
      }
    });
  }

  function renderCards(restaurants) {
    cardContainer.innerHTML = "";
    if (restaurants.length === 0) {
      cardContainer.innerHTML = "<p>해당 조건의 식당이 없습니다.</p>";
      return;
    }
    restaurants.forEach((restaurant) => {
      const card = createRestaurantCard(restaurant);
      card.addEventListener("click", () => openModal(restaurant));
      cardContainer.appendChild(card);
    });
  }

  function createRestaurantCard(restaurant) {
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
            <img class="card-img" src="${
              restaurant.imageUrl ||
              "https://via.placeholder.com/300x200.png?text=No+Image"
            }" alt="${restaurant.title}">
            <div class="card-content">
                <h3 class="card-title">${restaurant.title}</h3>
                <p class="card-category">${restaurant.category || "기타"}</p>
            </div>
        `;
    return card;
  }

  function openModal(restaurant) {
    document.getElementById("modal-img").src =
      restaurant.imageUrl ||
      "https://via.placeholder.com/600x250.png?text=No+Image";
    document.getElementById("modal-title").textContent =
      restaurant.title || "제목 없음";
    // ... (rest of modal population logic is the same)
    document.getElementById("modal-category").textContent =
      restaurant.category || "기타";
    document.getElementById("modal-description").textContent =
      restaurant.description || "설명 없음";
    document.getElementById("modal-visitor-reviews").textContent =
      restaurant.visitorReviews || "정보 없음";
    document.getElementById("modal-blog-reviews").textContent =
      restaurant.blogReviews || "정보 없음";
    document.getElementById("modal-address").textContent =
      restaurant.address || "정보 없음";
    document.getElementById("modal-phone").textContent =
      restaurant.phone || "정보 없음";
    document.getElementById("modal-hours").textContent = (
      restaurant.businessHours || "정보 없음"
    ).replace(/\\n/g, " ");

    const mapButton = document.getElementById("modal-map-button");
    if (restaurant.url) {
      mapButton.href = restaurant.url;
      mapButton.style.display = "inline-block";
    } else {
      mapButton.style.display = "none";
    }

    modal.classList.add("active");
  }

  function closeModal() {
    if (modal) modal.classList.remove("active");
  }

  // Event Listeners
  searchInput.addEventListener("input", debounce(applyFilters, 300));
  closeModalButton.addEventListener("click", closeModal);
  modal.addEventListener("click", (e) => {
    if (e.target === modal) closeModal();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && modal.classList.contains("active")) closeModal();
  });

  if (rouletteButton) {
    rouletteButton.addEventListener("click", () => {
      if (allRestaurants.length > 0) {
        // 1. 룰렛 오버레이 표시
        const overlay = document.getElementById("roulette-overlay");
        if (overlay) {
          overlay.style.display = "flex";
          // 2. 1.4초 후 룰렛 오버레이 숨기고 랜덤 식당 팝업
          setTimeout(() => {
            overlay.style.display = "none";
            const randomIndex = Math.floor(
              Math.random() * allRestaurants.length
            );
            const randomRestaurant = allRestaurants[randomIndex];
            openModal(randomRestaurant);
          }, 1400);
        }
      } else {
        alert("식당 데이터가 아직 준비되지 않았습니다.");
      }
    });
  }

  // TOP / DOWN 스크롤 이동 기능 + 동적 표시 제어
  const scrollTopBtn = document.getElementById("scroll-top");
  const scrollDownBtn = document.getElementById("scroll-down");
  if (scrollTopBtn) {
    scrollTopBtn.addEventListener("click", () => {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }
  if (scrollDownBtn) {
    scrollDownBtn.addEventListener("click", () => {
      window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
    });
  }
  const updateScrollButtons = () => {
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    const scrollBottom =
      window.innerHeight + scrollTop >= document.body.offsetHeight - 3; // 약간의 오차 허용
    if (scrollTopBtn) {
      if (scrollTop < 16) {
        scrollTopBtn.classList.add("hide");
      } else {
        scrollTopBtn.classList.remove("hide");
      }
    }
    if (scrollDownBtn) {
      if (scrollBottom) {
        scrollDownBtn.classList.add("hide");
      } else {
        scrollDownBtn.classList.remove("hide");
      }
    }
  };
  window.addEventListener("scroll", updateScrollButtons);
  window.addEventListener("resize", updateScrollButtons);
  // 페이지 최초 렌더에도 반영
  updateScrollButtons();
});
